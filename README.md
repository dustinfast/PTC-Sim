# PTCSim - Positive Train Control Simulator

PTCSim is a demonstration of a Positive Train Control (PTC) solution. It is a work in progress based on my experience developing LocoTracker, the Alaska Railroad Corporation's Locomotive Tracking Solution.

PTCSim implements broker-assisted communication between simulated locomotives and a Back Office Server (BOS) utilizing the Edge Message Protocol (EMP), Class C, Class D, and . User interaction is facilitated by a web interface dislaying current locomotive status and location via Google Earth display.
for the puroses of (PTC mandates)

The Rail Safety Improvment Act of 2008 was enacted by congress and required an estimated 100,000 miles of track to be equiped with PTC. As of 2018, no railroads  .. challenges - cost, existing infrastructure, 

Although this application is in the context of PTC, it's operation can be generalized.

## Applicaton Structure
PTC is large and complex - there is no off-the-shelf solution... mandates # TODO: prevention of train on train collisions, # TODO: over-speed derailments, # TODO: incursions into work zone limits, and # TODO: movement through misaligned track-switches with. Interoperability between different railroad is defined by Interoperable Train Control Messaging (ITCM)

PTCSim demonstrates a PTC implementation 

* **Back Office Server** Monitors each locomtive and displays real-time status, including location (via Google Earth) to it's web interface. Also provides a web-based computer-aided-dispatch (CAD) system for controlling track restrictions and  Additionally, has the ability to send commands to locomotives. - ATCS Message Addressing? I-ETMS msg encapsulation? 

* **Message Broker** An intermediary message translation and queueing system allowing reliable bi-directional communication between locomotives and the BOS over the physical messaging subsystem (i.e. 220 MHz base stations and waysides). # TODO: Protocol img

* **Track Simulator** Simulates a railroad and it's component rails, 220 MHz radio base stations, and waysides. Also includes simulated locomotives traveling on a track and broadcasting class C (specification/S-9356 Class D Spec.pdf) status messages to 220 MHz radio base-stations along the way.
Universal onboard  platform
Interoperable

TODO: Adaptive Braking Algorithm  Reliable, dependent braking

Challenges:
Reliable commo


Additionally, industry interoperability objectives dictate the use of Class C (
Class D messages are also typically implemented in PTC, to conform to industry interoperability objects.

EMP (Edge Message Protocol) as an upper layer message wrapper
– Class C is an IP based multicast protocol
– Class D is an IP based point to point protocol
– ITP (Interoperability Transport Protocol) as a lower layer routable transport protocol
• ITP is being tested for proof of concept using FRA funding


## Usage

Start the application with `./PTCSim` at the terminal, then navigate to http://localhost:5000/PTCSim.
  
Alternatively, the sim_loco, sim_broker, and sim_bos modules may be started from the terminal independently with `./sim_loco`, `./sim_broker` and `./sim_bos`, respectively. The latter serves the web interface.

**Dev Note:** Each module was developed with reusability and educational value in mind. The code base is well documented and free for use under the MIT Software License. Please credit the author accordingly.

## File Description

**config.dat** - Configuration information. For example, the message broker hostname/IP address.
**lib.py** - Shared classes and helper functions.  
**PTCSim.py** - Starts the necessary application processes
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
| message       |     locoID        : String,   |
|               |     speed        : Float,   |
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
|           msg   |   recipientID : String,   |
|               |     speed:      integer,      |
|               |     # TODO: restrictions: { ... }      |
|               |     direction:    'increasing' or 'decreasing'   |
|               |    }                                  |
|-------------------------------------------------------|

## Unimplemented

Some features typical in a PTC deployment are left unimplemented for the sake of demonstration simplicity. For example, no authentication, encryption, high availability, redundancy, or persistent data is implemented, and no TCP/IP session management is performed.  

## # TODO

Fix readme tables
Web: logtail/console output
Broker queue sizes in web output
Class D/Qpid?
bos loco cmds
Consolidate lib sections under one class each?
Ensure normalized app name - PTCSim
PEP8 file headers, imports, and docstrings (model after Track and connection?)
Privatize necessary members and do validation on public members
readme screenshots and high-level images
EMP spec file?
Catch specific socket conn errors w/ except socket.error as e:
py3
Wayside/Base modules and web output
One radio, one cell.
TrackCircuits - does not allow switch change when track occupied. Aids coll avoidance.
Switches (static, or random from static data) - 
