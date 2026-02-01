# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2026 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------
"""
Fyers HTTP error classes.
"""


class FyersApiError(Exception):
    """
    Fyers API error.

    Parameters
    ----------
    code : int
        The error code from Fyers API.
    message : str
        The error message.

    """

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Fyers API Error [{code}]: {message}")


class FyersAuthenticationError(FyersApiError):
    """
    Fyers authentication error.

    Raised when authentication fails due to invalid credentials or expired token.
    """

    def __init__(self, message: str) -> None:
        super().__init__(code=-1, message=message)


class FyersRateLimitError(FyersApiError):
    """
    Fyers rate limit error.

    Raised when the API rate limit is exceeded.
    """

    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(code=-2, message=message)


class FyersOrderError(FyersApiError):
    """
    Fyers order-related error.

    Raised when order submission, modification, or cancellation fails.
    """

    def __init__(self, code: int, message: str) -> None:
        super().__init__(code=code, message=message)


class FyersConnectionError(Exception):
    """
    Fyers connection error.

    Raised when connection to the Fyers API fails.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(f"Fyers Connection Error: {message}")
