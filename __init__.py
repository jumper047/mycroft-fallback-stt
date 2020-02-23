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
import subprocess
import json

from mycroft.messagebus.message import Message
from mycroft.skills.core import intent_file_handler
from mycroft import MycroftSkill


def ping(host):
    return subprocess.call(['ping', '-c', '1', host]) == 0


Stt = enum.Enum("Stt", ["Local", "Remote"])


class FallbackSttSkill(MycroftSkill):
    def __init__(self):
        super().__init__("FallbackSttSkill")
        self.force_local = False
        self.settings_fullfilled = False
        self.current_stt = None

    def initialize(self):
        self.settings_change_callback = self.reset_state
        self.add_event('recognizer_loop:no_internet', self.set_local_stt)
        self.schedule_repeating_event(self.check_stt_state, None, 300,
                                      "CheckSttState")
        self.reset_state()

    def check_stt_state(self):
        """Check stt server's current state and switch them if necessary"""
        if not self.settings_fullfilled:
            return None
        remote_avail = ping(self.remote_stt_addr)
        self.log.info("Remote STT server is %s",
                      "online" if remote_avail else "offline")
        if remote_avail and self.current_stt is Stt.Local:
            self.set_remote_stt()
        elif not remote_avail and self.current_stt is Stt.Remote:
            self.set_local_stt()

    def reset_state(self):
        """Recheck current state and apply apropriate settings"""

        # Check settings
        settings = [
            self.settings.get("remote_module"),
            self.settings.get("local_module"),
            self.settings.get("remote_settings"),
            self.settings.get("local_settings"),
            self.settings.get("remote_url")
        ]
        self.settings_fullfilled = None not in settings
        if not self.settings_fullfilled:
            self.log.info("Skill parameters not set, temoprary disabled")
            return None

        self.remote_stt_addr = self.settings["remote_url"]
        if ping(self.remote_stt_addr):
            self.set_remote_stt()
            self.log.info("Connected to local STT server")
        else:
            self.set_local_stt()
            self.log.info("Connected to remote STT server")

    @intent_file_handler("WhichStt.intent")
    def handle_which_stt(self, message):
        if self.current_stt == Stt.Remote:
            stt_type = self.settings["remote_module"]
            self.speak_dialog('remote.stt.used', data={'type': stt_type})
        elif self.current_stt == Stt.Local:
            stt_type = self.settings["local_module"]
            self.speak_dialog('local.stt.used', data={'type': stt_type})

    def set_remote_stt(self):
        new_config = {
            'stt': {
                'module': self.settings["remote_module"],
                self.settings["remote_module"]:
                json.loads(self.settings["remote_settings"])
            }
        }
        self.current_stt = Stt.Remote
        self._update_config(new_config)

    def set_local_stt(self):
        new_config = {
            'stt': {
                'module': self.settings["local_module"],
                self.settings["local_module"]: json.loads(self.settings["local_settings"])
            }
        }
        self.current_stt = Stt.Local
        self._update_config(new_config)

    def _update_config(self, config):
        from mycroft.configuration.config import (LocalConf, USER_CONFIG)
        user_config = LocalConf(USER_CONFIG)
        user_config.merge(config)
        user_config.store()
        self.bus.emit(Message('configuration.updated'))

    def shutdown(self):
        self.cancel_scheduled_event('CheckSttState')
        self.remove_event('recognizer_loop:no_internet')


def create_skill():
    return FallbackSttSkill()
