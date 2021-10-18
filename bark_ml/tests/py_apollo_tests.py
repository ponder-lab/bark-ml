# Copyright (c) 2021 fortiss GmbH
#
# Authors: Patrick Hart, Julian Bernhard, Klemens Esterle, and
# Tobias Kessler
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT


import unittest
import gym
import numpy as np

from bark.core.world import World
from bark.runtime.commons.parameters import ParameterServer
from bark_ml.environments.external_runtime import ExternalRuntime
from bark_ml.library_wrappers.lib_tf_agents.agents.sac_agent import BehaviorSACAgent
from bark_ml.observers.nearest_state_observer import NearestAgentsObserver
from bark_ml.environments.blueprints import ContinuousHighwayBlueprint
from bark_ml.environments.single_agent_runtime import SingleAgentRuntime
from bark_ml.behaviors.cont_behavior import BehaviorContinuousML  # pylint: disable=unused-import

class PyEnvironmentTests(unittest.TestCase):
  def setUp(self):
    params = ParameterServer()
    test_bp = ContinuousHighwayBlueprint(params)
    test_env = SingleAgentRuntime(blueprint=test_bp, render=False)
    test_env.reset()
    self.map_interface = test_env._world.map
    self.params = params

  def test_create_environment(self):
    map_interface = self.map_interface
    observer = NearestAgentsObserver()
    env = ExternalRuntime(
      map_interface=map_interface, observer=observer, params=self.params)
    # TODO: reset call
    self.assertTrue(isinstance(env.observation_space, gym.spaces.box.Box))

  def create_runtime_and_setup_empty_world(self, params):
    map_interface = self.map_interface
    observer = NearestAgentsObserver()
    env = ExternalRuntime(
      map_interface=map_interface, observer=observer, params=params)
    env.setupWorld()
    return env

  def test_setup_world(self):
    params = ParameterServer()
    env = self.create_runtime_and_setup_empty_world(params)
    self.assertTrue(isinstance(env._world, World))

  def test_add_ego_agent(self):
    params = ParameterServer()
    env = self.create_runtime_and_setup_empty_world(params)
    state = np.array([0, 0, 0, 0, 0])
    env.addEgoAgent(state)
    # self.assertEqual(env.ego_agent.state, state)

  def test_add_obstacle(self):
    params = ParameterServer()
    env = self.create_runtime_and_setup_empty_world(params)
    l = 4
    w = 2
    traj = np.array([[0, 0, 0, 0, 0]])
    obst_id = env.addObstacle(traj, l, w)
    # self.assertEqual(env._world.agents[obst_id].state, traj[0])
    env.clearAgents()
    self.assertEqual(len(env._world.agents), 0)

  def test_create_sac_agent(self):
    params = ParameterServer()
    map_interface = self.map_interface
    observer = NearestAgentsObserver()
    env = ExternalRuntime(
      map_interface=map_interface, observer=observer, params=params)
    env.ml_behavior = BehaviorContinuousML(params)
    sac_agent = BehaviorSACAgent(environment=env, params=params)
    env.ml_behavior = sac_agent
    self.assertTrue(isinstance(env.ml_behavior, BehaviorSACAgent))

  def test_generate_trajectory(self):
     # TODO: test env.generateTrajectory
     pass

if __name__ == '__main__':
  unittest.main()