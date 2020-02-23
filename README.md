# Mycroft Fallback STT Skill
Use local STT server if remote one is unavailable

## Description
**This plugin must be configured at settings page in home.mycroft.ai**
In settings must be setted local and remote recognizer modules, and their settings strings (same as in mycroft settings file), and host which will be pinged to detect is remote server available or not. Last one must be filled with hostname only (no http/https prefix, no port).
So, after mycroft's start plugin will periodically check host's availability and will switch to local stt server if it is offline and return to remote if internet will become up.
Also supports some voice commands to check state or switch recognizer.

## Examples
 - "Switch to remote server"
 - "Which engine are you using now?"

## Category
**Configuration**

## Tags
#system

