# PTC Sim - Positive Train Control Simulator

This application is a demonstration of a Positive Train Control (PTC) control applied to a simulated Track with virtual locomotives and communications infrastructure such as 220 MHz radio base-stations and messaging subsystem. It is a work in progress based on my experience developing LocoTracker, the Alaska Railroad Corporation's locomotive trackingsSolution. Tt contains no proprietary code, and is free under the MIT license.

Federal Railroad Administration's (FRA) PTC implementation deadline of 2015, and later extended to 2018, , mandated by the Act of...

PTC was mandated by congress in 2008 for all Class I or larger railroads with an implementation deadline of 2015. The deadline was later extended to 2018 after little progress was made due to technical challenges. That deadline was to prevent

PTC was mandated by congress to prevent:

* Train on train collisions
* Over-speed derailments
* Incursions into work zone limits
* Movement through misaligned track-switches
  
Interoperability between railroads is also required, asdefined by the Federal Railroad Administration's Interoperable Train Control (ITC) standard.

PTC Sim implements broker-assisted communication between simulated track devices (including locomotives) and a Back Office Server (BOS) utilizing the Edge Message Protocol (EMP). Locomotive tracking and computer-aided-dispatch (CAD) is facilitated by a web interface, where current component status and location is also displayed.

## Applicaton Structure

### Componenets

Each component exists as a seperate entity:

* **Back Office Server** : Provides CAD capabilities for communicating track restrictions to locomotives and displays real-time track device status and location via its website interface.

* **Message Broker**: An intermediate message translation system allowing bi-directional communication between track devices and the BOS.  Currently, each component transports EMP messages via TCP/IP only, but future versions may demonstrate Class C (IP based multicast protocol) and Class D (IP based point-to-point protocol) messaging.

* **Track Simulator**: Simulates a railroad and it's on-track devices, including:  
  * **Locomotives**:  Each locomotive travels along the track, broadcasting status messages and receiving CAD directives over its two 220 MHz radio transducers.b
  * **220 MHz Radio Base Stations**: Receives locomotive status messages and transmits them to the Message Broker via LAN.
  * **Waysides**: Receives status messages from it's attached switches via LAN, then broadcasts them over 220 MHz radio to the BOS.
  * **Switches**: Each switch sends its current position (OPEN, CLOSED, or ERROR) to its parent wayside at regular intervals.

### File Structure

**config.dat** - Application configuration information.
**lib_app.py** - Shared application-level class library.
**lib_msging.py** - Messaging subsytem class library.  
**lib_track.py** - Track simulation class library.
**start.py** - Starts the necessary application processes and runs the track simulator.  
**sim_bos.py** - The Back Office Server (AKA "BOS", pronounced like "boss").  
**sim_broker.py** - The Message Broker.  
**sim_track.py** - The Track Simulator.  
**track_bases.json** - JSON representation of the radio base stations facilitating locomotive communications. Each base station consists of a unique ID and the track mileposts it covers. Gaps in coverage area allowed, as are areas of overlapping coverage.  
**track_locos.json** - NOT IMPLEMENTED  
**track_rail.json** - JSON representation of the railroad track. Contains milepost markers and associated lat/long coordinates (in decimal degrees).
**track_waysides.json** - NOT IMPLEMENTED

### Unimplemented

Some features typical in a PTC deployment, such as authentication, encryption, high availability, redundancy, persistent data, and TCP/IP session management are left unimplemented for the sake of demonstration simplicity. In addition, the track simulation is currently restricted to a single branch.

### Message Specification

Adheres to EMP V4 (specified in S-9354.pdf) and uses fixed-format messages with variable-length header sections. The application-specific messaging implementation is defined as follows:

#### EMP Fields

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
| Body     | Data Element             | DYNAMIC        |
|          | CRC                   | DYNAMIC        |

#### Fixed-Format Messages

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

**6001**: Wayside Status Msgs - Contains a single key/value data element of the form:

```
    { sent      : (int) Unix time,
      ID        : (str) Unique wayside ID,
      Children  : (str) Key/value string of the form { ID: Status }
    }
```

**6002**: CAD to Locomotive Message - Contains a single key/value data element of the form:

```
    { sent      : (int) Unix time,
      ID        : (str) Intended recipient ID,
      Restrict  : (list) A list of restricted milepost ranges, as points
      }
```

## Usage

Start the application with `./start.py`, then navigate to http://localhost:5000/ptc_sim.
  
Alternatively, the BOS, Message Broker, and Track Simulator may be started independently with `./sim_bos`, `./sim_broker`, and `./sim_track`, respectively.


## # TODO

* Web: logtail/console output, broker queue sizes  
* PEP8 file headers, imports, and docstrings (model after Tack and connection, but move public members to class level-doc)  
* Privatize necessary members and do validation on public members  
* readme screenshots and high-level images  
* Catch specific socket conn errors w/ except socket.error  
* py3  
* TrackCircuits - does not allow switch change when track * occupied. Aids coll avoidance.  
* Switches
* bos does not quit start.py on CTRL + C, and only quits from sim_bos on CTRL+C: Turn off the CTRL + C msg. Or possibly redirect flask's stdout so exit kills it in sim_bos with a terminate()
* sim_track does not quit gracefully
* rename track_ to topology_
* Fictional track model
* Better exception bubbling from start.py
* Move appname to conf and use PTC-Sim