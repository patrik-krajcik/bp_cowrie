# Copyright (c) 2015 Michel Oosterhof <michel@oosterhof.net>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. The names of the author(s) may not be used to endorse or promote
#    products derived from this software without specific prior written
#    permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHORS ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

"""
This module contains connection code to work around issues with the
Granados SSH client library.
"""

from __future__ import annotations

import struct

from twisted.conch.ssh import common, connection
from twisted.internet import defer
from twisted.python import log


class CowrieSSHConnection(connection.SSHConnection):
    """
    Subclass this for a workaround for the Granados SSH library.
    Channel request for openshell needs to return success immediatly
    """

    def ssh_CHANNEL_REQUEST(self, packet):
        localChannel = struct.unpack(">L", packet[:4])[0]
        requestType, rest = common.getNS(packet[4:])
        wantReply = ord(rest[0:1])
        channel = self.channels[localChannel]

        log.msg(
            f"[DEBUG][connection.py][CowrieSSHConnection.ssh_CHANNEL_REQUEST] Received channel request type={requestType.decode(errors='ignore')} for channel={localChannel}, wantReply={wantReply}",
            system="cowrie"
        )

        if requestType == b"shell":
            wantReply = 0
            self.transport.sendPacket(
                connection.MSG_CHANNEL_SUCCESS,
                struct.pack(">L", self.localToRemoteChannel[localChannel]),
            )
            log.msg(
                f"[DEBUG][connection.py][CowrieSSHConnection.ssh_CHANNEL_REQUEST] Auto-accepted 'shell' request, sent CHANNEL_SUCCESS",
                system="cowrie"
            )

        d = defer.maybeDeferred(
            log.callWithLogger, channel, channel.requestReceived, requestType, rest[1:]
        )
        if wantReply:
            log.msg(
                f"[DEBUG][connection.py][CowrieSSHConnection.ssh_CHANNEL_REQUEST] Handling reply callback for request={requestType.decode(errors='ignore')}",
                system="cowrie"
            )
            d.addCallback(self._cbChannelRequest, localChannel)
            d.addErrback(self._ebChannelRequest, localChannel)
        return d
