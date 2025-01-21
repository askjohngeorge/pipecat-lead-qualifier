Title: Daily REST Helper - Pipecat

URL Source: https://docs.pipecat.ai/server/utilities/daily/rest-helpers

Markdown Content:
Daily REST Helper - Pipecat
===============
 

[Pipecat home page![Image 3: light logo](https://mintlify.s3.us-west-1.amazonaws.com/daily/logo/light.svg)![Image 4: dark logo](https://mintlify.s3.us-west-1.amazonaws.com/daily/logo/dark.svg)](https://docs.pipecat.ai/)

Search or ask...

Ctrl K

*   [Join the Discord](https://discord.gg/pipecat)

Search...

Navigation

Daily

Daily REST Helper

[Getting Started](https://docs.pipecat.ai/getting-started/overview)[Guides](https://docs.pipecat.ai/guides/introduction)[Server APIs](https://docs.pipecat.ai/server/introduction)[Client SDKs](https://docs.pipecat.ai/client/introduction)

*   [Community](https://discord.gg/pipecat)
*   [GitHub](https://github.com/pipecat-ai/pipecat)
*   [Examples](https://github.com/pipecat-ai/pipecat/tree/main/examples)
*   [Changelog](https://github.com/pipecat-ai/pipecat/blob/main/CHANGELOG.md)

*   [Server API Reference](https://docs.pipecat.ai/server/introduction)

##### API Reference

*   [Reference docs](https://pipecat-docs.readthedocs.io/)

##### Services

*   [Supported Services](https://docs.pipecat.ai/server/services/supported-services)
*   Transport
    
*   Speech-to-Text
    
*   LLM
    
*   Text-to-Speech
    
*   Speech-to-Speech
    
*   Image Generation
    
*   Video
    
*   Vision
    
*   Analytics & Monitoring
    

##### Base Service Classes

*   [Overview](https://docs.pipecat.ai/server/base-classes/introduction)
*   [Transport](https://docs.pipecat.ai/server/base-classes/transport)
*   [Speech Service](https://docs.pipecat.ai/server/base-classes/speech)
*   [LLM Service](https://docs.pipecat.ai/server/base-classes/llm)
*   [Text Processing](https://docs.pipecat.ai/server/base-classes/text)
*   [Media Service](https://docs.pipecat.ai/server/base-classes/media)

##### Frameworks

*   RTVI
    
*   [Pipecat Flows](https://docs.pipecat.ai/server/utilities/flows/pipecat-flows)

##### Utilities

*   Audio
    
*   Daily
    
    *   [Daily REST Helper](https://docs.pipecat.ai/server/utilities/daily/rest-helpers)
*   Filters
    
*   Observers
    
*   [Pipeline Heartbeats](https://docs.pipecat.ai/server/utilities/heartbeats)
*   [TranscriptProcessor](https://docs.pipecat.ai/server/utilities/transcript-processor)
*   [UserIdleProcessor](https://docs.pipecat.ai/server/utilities/user-idle-processor)

Daily

Daily REST Helper
=================

Classes and methods for interacting with the Daily API to manage rooms and tokens

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#classes)

Classes
-----------------------------------------------------------------------------------

### 

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#dailyroomsipparams)

DailyRoomSipParams

Configuration for SIP (Session Initiation Protocol) parameters.

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-display-name)

display\_name

string

default:

"sw-sip-dialin"

Display name for the SIP endpoint

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-video)

video

boolean

default:

false

Whether video is enabled for SIP

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-sip-mode)

sip\_mode

string

default:

"dial-in"

SIP connection mode

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-num-endpoints)

num\_endpoints

integer

default:

1

Number of SIP endpoints

Copy

```python
from pipecat.transports.services.helpers.daily_rest import DailyRoomSipParams

sip_params = DailyRoomSipParams(
    display_name="conference-line",
    video=True,
    num_endpoints=2
)
```

### 

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#dailyroomproperties)

DailyRoomProperties

Properties that configure a Daily room’s behavior and features.

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-exp)

exp

float

default:

"current\_time + 5 minutes"

Room expiration time as Unix timestamp

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-enable-chat)

enable\_chat

boolean

default:

false

Whether chat is enabled in the room

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-enable-prejoin-ui)

enable\_prejoin\_ui

boolean

default:

false

Whether the prejoin lobby UI is enabled

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-enable-emoji-reactions)

enable\_emoji\_reactions

boolean

default:

false

Whether emoji reactions are enabled

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-eject-at-room-exp)

eject\_at\_room\_exp

boolean

default:

true

Whether to eject participants when room expires

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-enable-dialout)

enable\_dialout

boolean

Whether dial-out is enabled

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-max-participants)

max\_participants

number

Maximum number of participants allowed in the room

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-sip)

sip

DailyRoomSipParams

SIP configuration parameters

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-sip-uri)

sip\_uri

dict

SIP URI configuration

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-start-video-off)

start\_video\_off

boolean

Whether the camera video is turned off by default

Copy

```python
import time
from pipecat.transports.services.helpers.daily_rest import (
    DailyRoomProperties,
    DailyRoomSipParams,
)

properties = DailyRoomProperties(
    exp=time.time() + 3600,  # 1 hour from now
    enable_chat=True,
    enable_emoji_reactions=True,
    sip=DailyRoomSipParams(display_name="conference")
)
```

### 

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#dailyroomparams)

DailyRoomParams

Parameters for creating a new Daily room.

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-name)

name

string

Room name (if not provided, one will be generated)

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-privacy)

privacy

string

default:

"public"

Room privacy setting (“private” or “public”)

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-properties)

properties

DailyRoomProperties

Room configuration properties

Copy

```python
import time
from pipecat.transports.services.helpers.daily_rest import (
    DailyRoomParams,
    DailyRoomProperties,
)

params = DailyRoomParams(
    name="team-meeting",
    privacy="private",
    properties=DailyRoomProperties(
        enable_chat=True,
        exp=time.time() + 7200  # 2 hours from now
    )
)
```

### 

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#dailyroomobject)

DailyRoomObject

Response object representing a Daily room.

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-id)

id

string

Unique room identifier

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-name-1)

name

string

Room name

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-api-created)

api\_created

boolean

Whether the room was created via API

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-privacy-1)

privacy

string

Room privacy setting

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-url)

url

string

Complete room URL

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-created-at)

created\_at

string

Room creation timestamp

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-config)

config

DailyRoomProperties

Room configuration

Copy

```python
from pipecat.transports.services.helpers.daily_rest import (
    DailyRoomObject,
    DailyRoomProperties,
)

# Example of what a DailyRoomObject looks like when received
room = DailyRoomObject(
    id="abc123",
    name="team-meeting",
    api_created=True,
    privacy="private",
    url="https://your-domain.daily.co/team-meeting",
    created_at="2024-01-20T10:00:00.000Z",
    config=DailyRoomProperties(
        enable_chat=True,
        exp=1705743600
    )
)
```

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#initialize-dailyresthelper)

Initialize DailyRESTHelper
-------------------------------------------------------------------------------------------------------------------------

Create a new instance of the Daily REST helper.

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-daily-api-key)

daily\_api\_key

string

required

Your Daily API key

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-daily-api-url)

daily\_api\_url

string

default:

"https://api.daily.co/v1"

The Daily API base URL

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-aiohttp-session)

aiohttp\_session

aiohttp.ClientSession

required

An aiohttp client session for making HTTP requests

Copy

```python
helper = DailyRESTHelper(
    daily_api_key="your-api-key",
    aiohttp_session=session
)
```

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#create-room)

Create Room
-------------------------------------------------------------------------------------------

Creates a new Daily room with specified parameters.

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-params)

params

DailyRoomParams

required

Room configuration parameters including name, privacy, and properties

Copy

```python
# Create a room that expires in 1 hour
params = DailyRoomParams(
    name="my-room",
    privacy="private",
    properties=DailyRoomProperties(
        exp=time.time() + 3600,
        enable_chat=True
    )
)
room = await helper.create_room(params)
print(f"Room URL: {room.url}")
```

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#get-room-from-url)

Get Room From URL
-------------------------------------------------------------------------------------------------------

Retrieves room information using a Daily room URL.

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-room-url)

room\_url

string

required

The complete Daily room URL

Copy

```python
room = await helper.get_room_from_url("https://your-domain.daily.co/my-room")
print(f"Room name: {room.name}")
```

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#get-token)

Get Token
---------------------------------------------------------------------------------------

Generates a meeting token for a specific room.

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-room-url-1)

room\_url

string

required

The complete Daily room URL

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-expiry-time)

expiry\_time

float

default:

"3600"

Token expiration time in seconds

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-owner)

owner

bool

default:

"True"

Whether the token should have owner privileges

Copy

```python
token = await helper.get_token(
    room_url="https://your-domain.daily.co/my-room",
    expiry_time=1800,  # 30 minutes
    owner=False
)
print(f"Meeting token: {token}")
```

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#delete-room-by-url)

Delete Room By URL
---------------------------------------------------------------------------------------------------------

Deletes a room using its URL.

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-room-url-2)

room\_url

string

required

The complete Daily room URL

Copy

```python
success = await helper.delete_room_by_url("https://your-domain.daily.co/my-room")
if success:
    print("Room deleted successfully")
```

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#delete-room-by-name)

Delete Room By Name
-----------------------------------------------------------------------------------------------------------

Deletes a room using its name.

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-room-name)

room\_name

string

required

The name of the Daily room

Copy

```python
success = await helper.delete_room_by_name("my-room")
if success:
    print("Room deleted successfully")
```

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#get-name-from-url)

Get Name From URL
-------------------------------------------------------------------------------------------------------

Extracts the room name from a Daily room URL.

[​](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#param-room-url-3)

room\_url

string

required

The complete Daily room URL

Copy

```python
room_name = helper.get_name_from_url("https://your-domain.daily.co/my-room")
print(f"Room name: {room_name}")  # Outputs: "my-room"
```

[SoundfileMixer](https://docs.pipecat.ai/server/utilities/audio/soundfile-mixer)[STTMuteFilter](https://docs.pipecat.ai/server/utilities/filters/stt-mute)

[x](https://x.com/pipecat_ai)[github](https://github.com/pipecat-ai/pipecat)[discord](https://discord.gg/pipecat)

[Powered by Mintlify](https://mintlify.com/preview-request?utm_campaign=poweredBy&utm_medium=docs&utm_source=docs.pipecat.ai)

On this page

*   [Classes](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#classes)
*   [DailyRoomSipParams](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#dailyroomsipparams)
*   [DailyRoomProperties](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#dailyroomproperties)
*   [DailyRoomParams](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#dailyroomparams)
*   [DailyRoomObject](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#dailyroomobject)
*   [Initialize DailyRESTHelper](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#initialize-dailyresthelper)
*   [Create Room](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#create-room)
*   [Get Room From URL](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#get-room-from-url)
*   [Get Token](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#get-token)
*   [Delete Room By URL](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#delete-room-by-url)
*   [Delete Room By Name](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#delete-room-by-name)
*   [Get Name From URL](https://docs.pipecat.ai/server/utilities/daily/rest-helpers#get-name-from-url)
