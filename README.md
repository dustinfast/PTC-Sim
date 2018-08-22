# PTC-Sim - Positive Train Control Simulator

This application is a demonstration of Positive Train Control (PTC) control applied to a simulated Track with virtual locomotives and communications infrastructure, such as 220 MHz radio base-stations, waysides, etc.. It is a work in progress based on my experience developing LocoTracker, the Alaska Railroad Corporation's locomotive tracking solution. It contains no proprietary code, and is free under the MIT license. Images obtained under the Creative Commons license. 

PTC was mandated by congress in 2008 for all Class I or larger railroads with an implementation deadline of 2015. The deadline was later extended to 2018 after little progress was made due to technical challenges. 

PTC's mandate is to prevent:

* Train on train collisions
* Over-speed derailments
* Incursions into work zone limits
* Movement through misaligned track-switches
  
Interoperability between railroads is also required, as defined by the Federal Railroad Administration's Interoperable Train Control (ITC) standard.

PTC-Sim implements broker-assisted communication between simulated track devices (including locomotives) and a Back Office Server (BOS) utilizing the Edge Message Protocol (EMP). Locomotive tracking and computer-aided-dispatch (CAD) is facilitated by a web interface, where current component status and location is displayed graphically.

## Applicaton Structure

### Components

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
**track_bases.json** - JSON representation of the radio base stations facilitating locomotive communications. Each base station consists of a unique ID and the track locations it covers. Gaps in coverage area allowed, as are areas of overlapping coverage.  
**track_locos.json** - NOT IMPLEMENTED  
**track_rail.json** - JSON representation of the railroad track. Contains location markers and associated lat/long coordinates (in decimal degrees).
**track_waysides.json** - NOT IMPLEMENTED

### Unimplemented

Some features typical in a PTC deployment, such as authentication, encryption, high availability, redundancy, persistent data, and connection session management are left unimplemented for the sake of demonstration simplicity. In addition, the track simulation is currently restricted to a single branch.

### Message Specification

Adheres to EMP V4 (specified in S-9354.pdf) and uses fixed-format messages with variable-length header sections. The application-specific messaging implementation is defined in docs/app_messaging_spec.md.

## Usage

Start the application with `./start.py`, then navigate to http://localhost:5000/ptc_sim.
  
Alternatively, the BOS, Message Broker, and Track Simulator may be started independently with `./sim_bos.py`, `./sim_broker.py`, and `./sim_track.py`, respectively.

### Dependencies

Flask, Jinja, Simple KML, JavaScript, AJAX, jQuery, GeoXML3, Google Maps Javascript API, 

 

## # TODO

* Not gracefully quitting due to connection obj threads?
* Web: logtail/console output, broker queue sizes  
* Catch specific socket conn errors w/ except socket.error  
* Fictional track model
* Better exception bubbling to start.py
* TrackDevice.err(str)?

* PEP8 file headers, imports, and docstrings (model after Tack and connection, but move public members to class level-doc)  
* Privatize necessary members and do validation on public members  
* readme screenshots and high-level images  
* py3 - >>> config = configparser.ConfigParser()
* Track Circuits, to aid col avoidance.  
* bos does not quit start.py on CTRL + C, and only quits from sim_bos on CTRL+C: Turn off the CTRL + C msg. Or possibly redirect flask's stdout so exit kills it in sim_bos with a terminate()
* Use multiprocessing instead of threading where reasonable
* Move msg spec (folder and readme) to /docs