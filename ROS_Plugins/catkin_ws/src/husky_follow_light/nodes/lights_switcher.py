#!/usr/bin/env python3
"""
This file is a state-machine prototype for the husky labyrinth demo.
"""

__author__ = 'HBP'

from collections import defaultdict

import rospy

import smach_ros
import smach
from smach import StateMachine, CBState

from gazebo_msgs.srv import SetLightProperties, GetLightProperties, SetLightPropertiesRequest
from geometry_msgs.msg import Pose, Quaternion, Point, Vector3
from std_msgs.msg import ColorRGBA

from smach_states import RobotPoseMonitorState


light_height = 2.80354

lights_position = {"spotlight_0": Point(7.07424, -2.36007, light_height),
                   "spotlight_1": Point(6.8531, 5.64267, light_height),
                   "spotlight_2": Point(0.10288, 4.60039, light_height),
                   "spotlight_3": Point(-0.375956, -0.074803, light_height),
                   "spotlight_4": Point(-6.3055, 0.079845, light_height),
                   "spotlight_5": Point(-6.35414, -5.44271, light_height),
                   "spotlight_6": Point(1.00474, -5.41132, light_height),
                   "spotlight_7": Point(0.532714, -10.7588, light_height),
                   "spotlight_8": Point(-0.11194, -6.84491, 4.37278)}


lights_orientation = defaultdict(lambda: Quaternion(0., 0., 0., 1.))

lights_orientation.update({"spotlight_4": Quaternion(-0.07493, 0, 0, 0.9972),
                           "spotlight_8": Quaternion(-0.04877, -0.42984, -0.8958, 0.1016)})


def name_to_pose(light_name):
    return Pose(position=lights_position[light_name],
                orientation=lights_orientation[light_name])


class SetLightPropertyState(smach_ros.ServiceState):
    """
    This state sets the light property
    """

    def __init__(self,
                 light_name,
                 cast_shadows,
                 diffuse, specular,
                 attenuation_constant, attenuation_linear, attenuation_quadratic,
                 direction=Vector3(x=0, y=0, z=-1)
                 ):
        """
        Creates a new service state to set the light

        :param light_name: The name of the light source that shall be triggered
        :param diffuse: The diffuse of the light.
        :param attenuation_constant: The constant attenuation.
        :param attenuation_linear: The linear attenuation.
        :param attenuation_quadratic: The quadratic attenuation.
        """
        super(SetLightPropertyState, self).__init__('/gazebo/set_light_properties',
                                                    SetLightProperties,
                                                    request=SetLightPropertiesRequest(
                                                        light_name,
                                                        cast_shadows,
                                                        diffuse,
                                                        specular,
                                                        attenuation_constant,
                                                        attenuation_linear,
                                                        attenuation_quadratic,
                                                        direction,
                                                        name_to_pose(light_name))
                                                    )


FINISHED = 'FINISHED'
ERROR = 'ERROR'
PREEMPTED = 'PREEMPTED'

ROBOT_ID = 'husky_model'


hotspots = [lambda ud, p: not ((6.2 < p.position.x < 8.0) and (-4.0 < p.position.y < -1.3)),
            lambda ud, p: not ((5.8 < p.position.x < 8.0) and (4.0 < p.position.y < 6.0)),
            lambda ud, p: not ((-0.29 < p.position.x < 0.36879) and (3.15 < p.position.y < 6.0)),
            lambda ud, p: not ((-2 < p.position.x < 1) and (-0.44192 < p.position.y < 0.79615)),
            lambda ud, p: not ((-6.69517 < p.position.x < -5.09197) and (
                    -1.25467 < p.position.y < 0.67082)),
            lambda ud, p: not ((-7.05016 < p.position.x < -4.26138) and (
                    -5.60488 < p.position.y < -4.69988)),
            lambda ud, p: not (
                    (0.18991 < p.position.x < 1.1271) and (-6.30064 < p.position.y < -4.69988))]


if __name__ == "__main__":
    rospy.init_node("light_switcher_sm")

    sm = StateMachine(outcomes=[FINISHED, ERROR, PREEMPTED])
    
    # register callback that stops the SM when exiting
    rospy.on_shutdown(lambda: sm.request_preempt())

    with sm:

       for i, hotspot in enumerate(hotspots):

            rospy.loginfo(f"Adding spotlight_{i}")
            StateMachine.add(
                f"set_light_red_{i}",
                SetLightPropertyState(light_name=f'spotlight_{i}',
                                      cast_shadows=True,
                                      diffuse=ColorRGBA(1.0, 0.0, 0.0, 1.0),
                                      specular=ColorRGBA(0.2, 0.2, 0.2, 1),
                                      attenuation_constant=0.8,
                                      attenuation_linear=0.01,
                                      attenuation_quadratic=0.001),
                transitions={'succeeded': f'wait_for_husky_light_{i}',
                             'aborted': ERROR,
                             'preempted': PREEMPTED}
            )

            StateMachine.add(
                f"wait_for_husky_light_{i}",
                RobotPoseMonitorState(ROBOT_ID, hotspot),
                transitions={'valid': f'wait_for_husky_light_{i}',
                             'invalid': f'set_light_blue_{i}',
                             'preempted': PREEMPTED}
            )


            if i >= len(hotspots) - 1:

                StateMachine.add(
                    f"set_light_blue_{i}",
                    SetLightPropertyState(light_name=f'spotlight_{i}',
                                          cast_shadows=True,
                                          diffuse=ColorRGBA(0.0, 0.0, 1.0, 1.0),
                                          specular=ColorRGBA(0.0, 0.0, 1.0, 1.0),
                                          attenuation_constant=0.8,
                                          attenuation_linear=0.01,
                                          attenuation_quadratic=0.001),
                    transitions={'succeeded': "set_light_red_end",
                                 'aborted': ERROR,
                                 'preempted': PREEMPTED}
                )


                StateMachine.add(
                    "set_light_red_end",
                    SetLightPropertyState(light_name=f'spotlight_{i+1}',
                                          cast_shadows=True,
                                          diffuse=ColorRGBA(1.0, 0.0, 0.0, 1.0),
                                          specular=ColorRGBA(1.0, 0.0, 0.0, 1.0),
                                          attenuation_constant=0.4,
                                          attenuation_linear=0.01,
                                          attenuation_quadratic=0.001),
                    transitions={'succeeded': 'wait_for_husky_end',
                                 'aborted': ERROR,
                                 'preempted': PREEMPTED}
                )

                StateMachine.add(
                    "wait_for_husky_end",
                    RobotPoseMonitorState(ROBOT_ID, lambda ud, p: not (
                                (-1.5 < p.position.x < 1.5) and (-14 < p.position.y < -9.58598))),
                    transitions={'valid': 'wait_for_husky_end',
                                 'invalid': FINISHED,
                                 'preempted': PREEMPTED}
                )

            else:
                StateMachine.add(
                    f"set_light_blue_{i}",
                    SetLightPropertyState(light_name=f'spotlight_{i}',
                                          cast_shadows=True,
                                          diffuse=ColorRGBA(0.0, 0.0, 1.0, 1.0),
                                          specular=ColorRGBA(0.0, 0.0, 1.0, 1.0),
                                          attenuation_constant=0.4,
                                          attenuation_linear=0.01,
                                          attenuation_quadratic=0.001),
                    transitions={'succeeded': f"set_light_red_{i+1}",
                                 'aborted': ERROR,
                                 'preempted': PREEMPTED}
                )

    

    sm.execute()

    rospy.spin()
