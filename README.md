# PTCSim - Positive Train Control Simulator

This application is a demonstration of a Positive Train Control (PTC) implementation. It is a work in progress based on my experience developing LocoTracker, the Alaska Railroad Corporation's Locomotive Tracking Solution.

PTCSim implements broker-assisted communication between simulated locomotives and a Back Office Server (BOS) utilizing the Edge Message Protocol (EMP). Locomotive tracking and computer-aided-dispatch (CAD) is facilitated by a web interface, where current locomotive status and location is also displayed. # TODO: Web Screenshot

## Applicaton Structure

PTC was mandated by congress to # TODO: prevent train on train collisions, # TODO: over-speed derailments, # TODO: incursions into work zone limits, and # TODO: movement through misaligned track-switches. Interoperability between railroads is required and defined by the Federal Railroad Administration's Interoperable Train Control (ITC) standard. PTCSim implements these requirements within the following framework:

### Componenets

* **Back Office Server** : Provides CAD capabilities for communicating track restrictions to locomotives, and displays real-time locomotive status and location via its website interface.

* **Message Broker**: An intermediate message translation system allowing bi-directional communication between track components (including locomotives) and the BOS over the railroad's communications infrastructure.  Currently, PTCSim transports EMP messages via TCP/IP only, but future versions may also demonstrate Class C (IP based multicast protocol) and Class D (IP based point-to-point protocol) communications.

* **Track Simulator**: Simulates a railroad and it's on-track devices, including:  
  * **220 MHz Radio Base Stations**: Receives locomotive status messages and transmits them to the Message Broker via LAN.
  * **Locomotives**:  Each locomotive travels along the track, broadcasting status messages over two 220 MHz radio transducers and receiving CAD directives.
  * **Waysides**: Receives status messages from it's attached switches, then encapsulates them for broadcast over 220 MHz radio.
  * **Switches**: Each switch sends its current position (OPEN, CLOSED, or ERROR) to its parent wayside at regular intervals.

### File Structure

**config.dat** - Application configuration information. For example, the message broker hostname/IP address.  
**lib.py** - Shared classes and helper functions.  
**start.py** - Starts the necessary application processes and runs the track simulator.  
**sim_bos.py** - The Back Office Server, (AKA "BOS", pronounced like "boss").  
**sim_broker.py** - The Message Broker.  
**sim_track.py** - The Track Simulator.  
**track_bases.json** - JSON representation of the radio base stations facilitating locomotive communications. Each base station consists of a unique ID and the track mileposts it covers. Gaps in coverage area allowed, as are areas of overlapping coverage.  
**track_locos.json** - NOT IMPLEMENTED  
**track_rail.json** - JSON representation of the railroad track. Contains milepost markers and associated lat/long coordinates (in decimal degrees).
**track_waysides.json** - NOT IMPLEMENTED

## Usage

Start the application with `./start.py`, then navigate to http://localhost:5000/PTCSim.
  
Alternatively, the BOS, Message Broker, and Track Simulator may be run independently with `./sim_bos`, `./sim_broker`, and `./sim_track`, respectively.

**Note:** Each module was developed with reusability and educational value in mind. The code base is well documented and free for use under the MIT Software License. Please credit the author accordingly.

## Message Specification

Adheres to EMP V4 (specified in S-9354.pdf) and uses fixed-format messages with variable-length header sections. The application-specific messaging implementation is defined as follows:

### EMP Fields

| Section      | Field | Value                          |
|--------------|-------|--------------------------------|
| Common Header        | EMP Header Version | 4         |
|                      | Message Type/ID     | DYNAMIC  |
|          | Message Version       | 1              |
|          | Flags                 | 0000 0000      |
|          | Body Size             | DYNAMIC        |
| Optional Header                  | None/Unused        ||
| Variable Length Header | Variable Header Size  | DYNAMIC |
|          | Network Time to Live  | 120            |
|          | Quality of Service    | 0              |
|          | Sender Address        | DYNAMIC        |
|          | Destination Address   | DYNAMIC        |
| Body     | Body/Data             | DYNAMIC        |
|          | CRC                   | DYNAMIC        |

### Fixed-Format Messages

**6000**: Locomotive Status Message - Contains a single key/value data element of the form: 

```
    { sent      : (int) Unix time,
      locoID    : (str) Unique locomotive ID,
      speed     : (float) Current speed,
      heading   : (float) Current Heading,
      direction : (str) 'increasing' or 'decreasing',
      milepost  : (float) Nearest milepost ID,
      lat       : (float) Current GPS latitude in d.d.,
      long      : (float) Current GPS longitude in d.d.,
      bpp       : (float) Current Brake Pipe Pressure,
      base      : (Integer) ID of current base station,
      bases     : (list) All receiving base station IDs
     }
```

**6002**: CAD to Locomotive Message - Contains a single key/value data element of the form:

```
    { sent      : (int) Unix time,
      ID        : (str) Intended recipient ID,
      Restrict  : (list) A list of restricted milepost ranges, as points
      }
```

**6001**: Wayside Status Msgs - Contains a single key/value data element of the form:

```
    { sent      : (int) Unix time,
      ID        : (str) Unique wayside ID,
      Children  : (str) Key/value string of the form { ID: Status }
    }
```
## Unimplemented

Some features typical in a PTC deployment are left unimplemented for the sake of demonstration simplicity. For example, no authentication, encryption, high availability, redundancy, or persistent data is implemented, and no TCP/IP session management is performed.  
Currently, the railroad simulated is restricted to a single branch.

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
