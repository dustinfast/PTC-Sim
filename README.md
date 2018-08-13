# loco_sim

This application is  based on my experience in Postive Train Control. It demonstrates broker-assisted communication between simulated locomotives and a Back Office Server (BOS) using the Edge Message Protocol (EMP) and consists of three top-level parts:
  
**Locomotive Simulator (sim_loco.py)**  
A simulated locomotive (loco) traveling on a track and connecting to track-section specific radio base stations for the purpose of communicating its status (location, speed, etc.) to the BOS at regular intervals. Additionally, locos fetch messages addressed to them in order to receive speed and direction of travel adjustments from the BOS.  

Note: Multiple instances of the locomotive simulator may instantiated. However, tracks exist seperately for each instance. I.e. Virtual locos may occupy identical track sections simultaneously without collision.

**Message Broker (sim_broker.py)**  
Brokers messages between the BOS and locomotives, allowing bi-directional communication. Loco-to-BOS msgs are sent to the broker to be fetched by the BOS, and BOS-to-loco msgs are sent to the broker to be fetched by the loco.

**Back Office Server (sim_bos.py)**  
The BOS monitors each locomotive and displays status graphically via its website and Google Earth mapping. Additionally, the BOS may send the locomotive commands.

## File Description

**conf.dat** - Configuration information. For example, the message broker hostname/IP address.  
**lib.py** - Shared classes and helper functions.  
**sim_bos.py** - The Back Office Server, or "BOS" (pronounced like "boss").  
**sim_broker.py** - The QPID message broker.  
**sim_loco.py** - The locomotive simulator.
**track_bases.json** - JSON representation of the base stations providing radio communication to on-track locos. Each base station consists of a unique ID and the on-track mileposts it provides coverage for. Gaps in coverage area allowed, as are areas of overlapping coverage.  
**track_rail.json** - JSON representation of a railroad track. Contains milepost markers and associated lat/long coordinates (in decimal degrees) of each. In this particular instance, the track is a model of the Alaska Railroad's main branch.

## Message Specification

Adheres to EMP V4 (specified in msg_spec/S-9354.pdf) with fixed-format messages having a variable header section. This messaging implementation is defined as the following:

**EMP Fields Values**
|---------------------------------------------------|
| Section  | Field / Value                          |
|---------------------------------------------------|
| Common   | EMP Header Version    : 4              |
| Header   | Message Type/ID       : DYNAMIC        |
|          | Message Version       : 1              |
|          | Flags                 : 0              |
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

**Fixed-Format Messages, by ID**
|-------------------------------------------------------|
| ID / Desc     | Data Element, by index                |
|-------------------------------------------------------|
| 6000:         | 0: A key/value string of the form     |
| Loco status   |    {sent          : Unix Time,         |
| message       |     loco          : 4 digit integer,   |
|               |     speed        : integer,   |
|               |     direction    : string,   |
|               |     heading        : integer,   |
|               |     lat     : Integer,           |
|               |     long    : Integer,           |
|               |     base : Integer            |
|               |    }                                  |
                    {'sent': time.now(),
                       'loco': self.ID,
                       'speed': self.speed,
                       'heading': self.heading,
                       'lat': self.loco.milepost.lat,
                       'long': self.loco.milepost.long,
                       'base': self.loco.current_base}
|-------------------------------------------------------|
| 6001:         | 0: A key/value string of the form     |
| BOS to loco   |    {sent    : Unix Time,         |
| command msg   |     loco : 4 digit integer,   |
|               |     speed:      integer,      |
|               |     dir:    'incresing' or 'decreasing'   |
|               |    }                                  |
|-------------------------------------------------------|

## Usage
  
**Demonstration**
For a demonstration of all packages, enter `./demo.py` at the terminal, then navigate to http://localhost/loco_sim

**Command Line**
The loco sim, message broker, and BOS each provide a command line interface when run independently from the terminal. Start each with `./sim_loco.py`, `/sim_broker.py` and `./sim_bos.py`, respectively.

**Dev**
Each module is well documented and was developed with re-usability and educational value in mind. It is free for use under the MIT Software License.

## Caveats

This application takes several liberties for the sake of simplicity in demonstration. For example, no high availability, redundancy, or persistent data is implmented, and no TCP/IP session management is performed (connections are created and torn down each time a msg is sent or fetched). In a typical PTC scenario, these features are likely to be mandatory.

## # TODO

Class D/Qpid?
Web input
bos loco cmds - need contextual repl first
Shebang permissions
Move prompt below console output
Consolidate lib sections under one class each?
Ensure normalized app name
Better output on connection error
Standardize file headers and docstrings (PEP8)
Privatize necessary members and do validation on public members
readme screenshots
TrackCircuits
Flask
