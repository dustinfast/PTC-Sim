# PTC_SIM - Locomotive Back Office Server Simulation

This application is based on my experience in Postive Train Control (PTC) and demonstrates broker-assisted communication between simulated locomotives and a Back Office Server (BOS). Messaging is accomplished using the Edge Message Protocol (EMP), and user interaction occurs via web interface.

PTC_SIM consists of the following top-level components:

**Back Office Server with Web Interface**  
The BOS monitors each locomotive and displays the status of each graphically, including real-time locations via Google Earth. Additionally, the BOS may send commands to locomotives.

**Locomotive Simulator**  
Simulated locomotives (loco) traveling on the given track and connecting to radio base stations along the way for the purpose of communicating their status (location, speed, etc.) to the BOS at regular intervals. Additionally, locomos may fetch messages enqueued at the broker from the BOS containing speed and direction of travel adjustments.  
  
Note: Multiple instances of the locomotive simulator may instantiated. However tracks exist seperately across each instance. I.e., Virtual locos may occupy identical track sections simultaneously without collision.

**Message Broker**  
The backbone of the messaging subsystem, the broker allows bi-directional communication between locos and the BOS.

## Usage

Start the application with `./PTC_SIM` at the terminal, then navigate to http://localhost:5000/PTC_SIM.
  
Alternatively, the sim_loco, sim_broker, and sim_bos modules may be started from the terminal independently with `./sim_loco`, `./sim_broker` and `./sim_bos`, respectively. The latter serves the web interface.

**Dev Note:** Each module was developed with reusability and educational value in mind. The code base is well documented and free for use under the MIT Software License. Please credit the author accordingly.

## File Description

**config.dat** - Configuration information. For example, the message broker hostname/IP address.
**lib.py** - Shared classes and helper functions.  
**PTC_SIM.py** - Starts the necessary application processes
**sim_bos.py** - The back office server, (AKA "BOS", pronounced like "boss").  
**sim_broker.py** - The message broker.  
**sim_loco.py** - The locomotive simulator.
**track_bases.json** - JSON representation of the radio base stations facilitating locomotive communications. Each base station consists of a unique ID and the track mileposts it covers. Gaps in coverage area allowed, as are areas of overlapping coverage.  
**track_rail.json** - A JSON representation of a railroad track. Contains milepost markers and associated lat/long coordinates (in decimal degrees). In this particular instance, the track is a model of the Alaska Railroad's main branch.

## Message Specification

Adheres to EMP V4 (specified in S-9354.pdf) and uses fixed-format messages with variable-length header sections. The application-specific messaging implementation is defined as follows:

**EMP Fields Values**
|---------------------------------------------------|
| Section  | Field / Value                          |
|---------------------------------------------------|
| Common   | EMP Header Version    : 4              |
| Header   | Message Type/ID       : DYNAMIC        |
|          | Message Version       : 1              |
|          | Flags                 : 0000 0000      |
|          | Body Size             : DYNAMIC        |
|---------------------------------------------------|
| Optional | Unused                                 |
| Header   |                                        |
|---------------------------------------------------|
| Variable | Variable Header Size  : DYNAMIC        |
| Length   | Network Time to Live  : 120            |
| Header   | Quality of Service    : 0              |
|          | Sender Address        : DYNAMIC        |
|          | Destination Address   : DYNAMIC        |
|----------|----------------------------------------|
| Body     | Body/Data             : DYNAMIC        |
|          | CRC                   : DYNAMIC        |
|---------------------------------------------------|

**Fixed-Format Messages**
|-------------------------------------------------------|
| ID / Desc     | Data Element                          |
|-------------------------------------------------------|
| 6000:         | A key/value string of the form     |
| Loco status   |    {sent          : Unix Time,         |
| message       |     loco          : 4 digit integer,   |
|               |     speed        : integer,   |
|               |     heading        : Float,   |
|               |     direction    : 'increasing' or 'decreasing'
|               |     milepost    : Float,   |
|               |     lat     : Float,           |
|               |     long    : Float,           |
|               |     base : Integer            |
|               |     bases : List           |
|               |    }                                  |
|-------------------------------------------------------|
| 6001:         | A key/value string of the form     |
| BOS to loco   |    {sent    : Unix Time,         |
| command msg   |     loco : 4 digit integer,   |
|               |     speed:      integer,      |
|               |     direction:    'increasing' or 'decreasing'   |
|               |    }                                  |
|-------------------------------------------------------|

## Concessions

Some features typical in a PTC deployment are left unimplemented for the sake of demonstration simplicity. For example, no authentication, encryption, high availability, redundancy, or persistent data is implemented, and no TCP/IP session management is performed.

## # TODO

Fix readme tables
Web: logtail/console output
Broker queue sizes in web output
Class D/Qpid?
bos loco cmds
Consolidate lib sections under one class each?
Ensure normalized app name - PTC_SIM
PEP8 file headers, imports, and docstrings (model after Track?)
Privatize necessary members and do validation on public members
readme screenshots and high-level images
TrackCircuits
EMP spec file?
Catch specific socket conn errors w/ except socket.error as e:
py3
Wayside/Base modules and web output
