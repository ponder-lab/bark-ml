# Copyright (c) 2020 fortiss GmbH
#
# Authors: Patrick Hart
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

import logging
import tensorflow as tf
from enum import Enum
from graph_nets import modules
from graph_nets import utils_tf
from graph_nets import utils_np
from graph_nets.graphs import GraphsTuple
import sonnet as snt

# bark-ml
from bark.runtime.commons.parameters import ParameterServer
from bark_ml.observers.graph_observer import GraphObserver
from bark_ml.observers.graph_observer_v2 import GraphObserverV2
from bark_ml.library_wrappers.lib_tf_agents.networks.gnn_wrapper import GNNWrapper



def make_mlp_model(layer_config=None):
  """Instantiates a new MLP, followed by LayerNorm.
  The parameters of each new MLP are not shared with others generated by
  this function.
  Returns:
    A Sonnet module which contains the MLP and LayerNorm.
  """
  return snt.Sequential([
    snt.nets.MLP([80, 80],
    w_init=tf.keras.initializers.GlorotUniform(),
    b_init=tf.keras.initializers.Constant(0.001),
    # activation=tf.keras.activations.relu,
    activate_final=True)
  ])

class MLPGraphNetwork(snt.Module):
  """GraphNetwork with MLP edge, node, and global models."""
  def __init__(self,
               edge_block_opt,
               node_block_opt, 
               global_block_opt,
               name="MLPGraphNetwork"):
    super(MLPGraphNetwork, self).__init__(name=name)
    self._network = modules.GraphNetwork(
      make_mlp_model,
      make_mlp_model,
      make_mlp_model,
      edge_block_opt=edge_block_opt,
      node_block_opt=node_block_opt,
      global_block_opt=global_block_opt)

  def __call__(self, inputs):
    return self._network(inputs)


class MLPGraphIndependent(snt.Module):
  """GraphIndependent with MLP edge, node, and global models."""

  def __init__(self, name="MLPGraphIndependent"):
    super(MLPGraphIndependent, self).__init__(name=name)
    self._network = modules.GraphIndependent(
        edge_model_fn=make_mlp_model,
        node_model_fn=make_mlp_model,
        global_model_fn=make_mlp_model)

  def __call__(self, inputs):
    return self._network(inputs)

class GSNTWrapper(GNNWrapper):
  """
  Implements a graph lib.
  """

  def __init__(self,
               params=ParameterServer(),
               name='GNST',
               output_dtype=tf.float32):
    """
    Initializes a GSNTWrapper instance.

    Args:
    params: A `ParameterServer` instance containing the parameters
      to configure the GNN.
    graph_dims: A tuple containing the three elements
      (num_nodes, len_node_features, len_edge_features) of the input graph.
      Needed to properly convert observations back into a graph structure 
      that can be processed by the GNN.
    name: Name of the instance.
    output_dtype: The dtype to which the GNN output is casted.
    """
    super(GSNTWrapper, self).__init__(
      params=params,
      name=name,
      output_dtype=output_dtype)
    self._num_message_passing_layers = params["ML"]["GSNT"][
      "NumMessagePassingLayers", "Number of message passing layers", 2]
    self._embedding_size = params["ML"]["GSNT"][
      "EmbeddingSize", "Embedding size of nodes", 80]
    # self._activation_func = params["ML"]["GAT"][
    #   "Activation", "Activation function", "elu"]
    # self._num_attn_heads = params["ML"]["GAT"][
    #   "NumAttnHeads", "Number of attention heads to be used", 4]
    # self._dropout_rate = params["ML"]["GAT"][
    #   "DropoutRate", "", 0.]
    self._layers = []
    # initialize network & call func
    self._init_network()
    self._call_func = self._init_call_func
    
  def _init_network(self):
    edge_block_opt = {
      "use_edges": True,
      "use_receiver_nodes": True,
      "use_sender_nodes": True,
      "use_globals": False
    }
    node_block_opt = {
      "use_received_edges": True,
      "use_nodes": True,
      "use_globals": False
    }
    self._encoder = MLPGraphIndependent()
    self._gnn_core = MLPGraphNetwork(
      edge_block_opt, node_block_opt, global_block_opt=None)
    self._decoder = MLPGraphIndependent()
    

  def _init_call_func(self, observations, training=False):
    """Graph nets implementation"""
    node_vals, edge_indices, node_lens, edge_lens, globals, edge_vals = GraphObserverV2.graph(
      observations=observations, 
      graph_dims=self._graph_dims,
      dense=True)
    batch_size = tf.shape(observations)[0]
    
    input_graph = GraphsTuple(
      nodes=tf.cast(node_vals, tf.float32),  # validate
      edges=tf.cast(edge_vals, tf.float32),  # validate
      globals=tf.cast(globals, tf.float32),
      receivers=tf.cast(edge_indices[:, 1], tf.int32),  # validate
      senders=tf.cast(edge_indices[:, 0], tf.int32),  # validate
      n_node=node_lens,  # change
      n_edge=edge_lens)  

    # print(input_graph)
    
    # encoding
    latent = self._encoder(input_graph)
    latent0 = latent
    # message passing
    for _ in range(0, 3):
      core_input = utils_tf.concat([latent0, latent], axis=1)
      latent = self._gnn_core(core_input)
      
    # decoder
    out = self._decoder(latent)

    node_values = tf.reshape(out.nodes, [batch_size, -1, self._embedding_size])
    return node_values

