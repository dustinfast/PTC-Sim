# PTC-Sim - Positive Train Control Simulator

This application is A Positive Train Control (PTC) Back Office Server (BOS) with web interface, track and locomotive simulators, and Edge Message Protocol (EMP) messaging subsystems. Development has begun with the intention of growing into an open-source PTC solution after experiencing first-hand the difficulties railroads are experiencing as they attempt to meet PTC implementation deadlines imposed by congress in 2008. It is a work in progress and distributable free under the MIT license. Images were obtained under the Creative Commons license.

PTC's mandate is to prevent:

* Train on train collisions
* Over-speed derailments
* Incursions into work zone limits
* Movement through misaligned track-switches
  
Interoperability between railroads is also required, as defined by the Federal Railroad Administration's Interoperable Train Control (ITC) standard.

PTC-Sim currently implements broker-assisted EMP communication between simulated on-track devices (locomotives and 220 MHz radio base-stations) and the BOS. Locomotive tracking and computer-aided-dispatch (CAD) is facilitated by a web interface, where current device status and location are displayed graphically.

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

### File Hierarchy

**config.dat** - Application configuration information.
**lib_app.py** - Shared application-level class library.
**lib_msg.py** - Messaging subsytem class library.  
**lib_track.py** - Track simulation class library, Including Locomotive and Base Station classes.
**lib_web.py** - The BOS' web interface library.
**start.py** - Starts the PTC-Sim wholistically.
**sim_bos.py** - The Back Office Server (AKA "BOS", pronounced like "boss") and it's web interface.  
**sim_broker.py** - The Message Broker.
**sim_track.py** - The Track Simulator.  
**track_bases.json** - JSON representation of the radio base stations facilitating locomotive communications. Each base station consists of a unique ID and the track locations it covers. Gaps in coverage area allowed, as are areas of overlapping coverage.  
**track_locos.json** - JSON representation of a railroads locomotives.
**track_rail.json** - JSON representation of the track rails. Contains location markers and associated lat/long coordinates (in decimal degrees). In this demonstration instance, the track is a model of the Alaska Railroad Corporation's main branch, with data obtained via Google's Map API.
**track_waysides.json** - NOT IMPLEMENTED

### Unimplemented

Some features typical in a PTC deployment, such as authentication, encryption, high availability, redundancy, persistent data, and connection session management are left unimplemented for the sake of demonstration simplicity. In addition, the track simulation is currently restricted to a single branch.

### Message Specification

Adheres to EMP V4, as specified by docs/S-9354.pdf. Application-specific message implementation is defined in docs/app_messaging_spec.md.

## Usage

From a Linux terminal, start the application with `./start.py`, then navigate to http://localhost:5000/ptc_sim.
  
Alternatively, the BOS, Message Broker, and Track Simulator may be started independently with `./sim_bos.py`, `./sim_broker.py`, and `./sim_track.py`, respectively.

### Dependencies

Requires Python 2.7. All other dependencies are managed by the application, including Flask, Jinja, JavaScript, AJAX, jQuery, GeoXML3, and the Google Maps API.

## # TODO

* Connection timeout watcher causes no graceful quit
* Web Output: logs and broker queue sizes
* Better exception bubbling to start.py
* Trackline legend: No 220 coverage, restricted, etc.
* Broker queue msg expire time
  
* Move JSON data to SQL
* Ensure PEP8 for file headers, imports, and docstrings (model after Tack and connection, but move public members to class level-doc)  
* Privatize necessary members and do validation on public members
* Readme screenshots and high-level images
* Move to py3 - config = configparser.ConfigParser()
* Track Circuits, to aid col avoidance.  
* Use multiprocessing instead of threading where reasonable