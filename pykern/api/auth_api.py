"""?

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.api import util
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.quest


class AuthAPI(pykern.quest.API):

    #: Defaults version number but allows override
    VERSION = util.AUTH_API_VERSION

    async def api_authenticate_connection(self, api_args):
        """Process AuthRequest from server

        api_args:
            token (str): secret value evaluated by `AuthAPI`
            version (int): protocol version
        Args:
            api_args (PKDict): what to validate
        Returns:
            Result: validation result
        """
        if (v := api_args.get("version")) != self.VERSION:
            raise util.APIProtocolError(f"invalid version={v}, expected={self.VERSION}")
        if (t := self.token()) is not None and t != api_args.token:
            # Do not log token
            raise util.APIForbidden()
        return PKDict()

    def token(self):
        return None
