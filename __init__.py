# Copyright 2020, jumper047.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import enum
import re
import subprocess

from mycroft.messagebus.message import Message
from mycroft.skills.core import intent_file_handler
from mycroft import MycroftSkill


def ping(host):
    return subprocess.call(['ping', '-c', '1', host]) == 0


Stt = enum.Enum("Stt", ["Local", "Remote"])


class FallbackSttSkill(MycroftSkill):
    def __init__(self):
        super().__init__("FallbackSttSkill")
        self.host_re = r'^http(s|)://(?P<host>.*)(:[0-9]+)/.*$'
        self.current_stt = None
        self.settings["remote_uri"] = 'http://192.168.1.35:8301/decode'
        self.settings["remote_module"] = 'kaldi'
        self.settings["local_module"] = 'kaldi'
        self.settings["local_uri"] = 'http://localhost:8301/decode'

    def initialize(self):
        self.settings_change_callback = self.reset_state
        self.add_event('recognizer_loop:no_internet', self.toggle_stt)
        self.schedule_repeating_event(self.check_stt_state, None, 300,
                                      "CheckSttState")
        self.reset_state()

    def check_stt_state(self):
        """Check stt server's current state and switch them if necessary"""

        remote_avail = ping(self.remote_stt_addr)
        self.log.info("Remote STT server is %s",
                      "online" if remote_avail else "offline")
        if (remote_avail and self.current_stt is Stt.Local) or (
                not remote_avail and self.current_stt is Stt.Remote):
            self.toggle_stt()

    def reset_state(self):
        """Recheck current state and apply apropriate settings"""

        self.remote_stt_addr = re.match(
            self.host_re, self.settings["remote_uri"]).group("host")
        if ping(self.remote_stt_addr):
            self.set_stt(Stt.Local)
            self.current_stt = Stt.Local
            self.log.info("Connected to local STT server")
        else:
            self.set_stt(Stt.Remote)
            self.current_stt = Stt.Remote
            self.log.info("Connected to remote STT server")

    @intent_file_handler("WhichStt.intent")
    def handle_which_stt(self, message):
        if self.current_stt == Stt.Remote:
            stt_type = self.settings["remote_module"]
            self.speak_dialog('remote.stt.used', data={'type': stt_type})
        elif self.current_stt == Stt.Local:
            stt_type = self.settings["local_module"]
            self.speak_dialog('local.stt.used', data={'type': stt_type})

    def toggle_stt(self):
        if self.current_stt == Stt.Local:
            self.log.info("Switching to remote STT")
            self.set_stt(Stt.Remote)
        elif self.current_stt == Stt.Remote:
            self.log.info("Switching to local STT")
            self.set_stt(Stt.Local)
        else:
            self.reset_state()

    def set_stt(self, stt_name):
        if stt_name == Stt.Local:
            new_config = {
                'stt': {
                    'module': self.settings["local_module"],
                    self.settings["local_module"]: {
                        "uri": self.settings["local_uri"]
                    }
                }
            }
        elif stt_name == Stt.Remote:
            new_config = {
                'stt': {
                    'module': self.settings["remote_module"],
                    self.settings["remote_module"]: {
                        "uri": self.settings["remote_uri"]
                    }
                }
            }
        from mycroft.configuration.config import (LocalConf, USER_CONFIG,
                                                  Configuration)

        user_config = LocalConf(USER_CONFIG)
        user_config.merge(new_config)
        user_config.store()
        self.bus.emit(Message('configuration.updated'))
        self.current_stt = stt_name

    def shutdown(self):
        self.cancel_scheduled_event('CheckSttState')


def create_skill():
    return FallbackSttSkill()
