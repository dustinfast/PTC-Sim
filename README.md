# PTC-Sim - Positive Train Control Simulator

This application is A Positive Train Control (PTC) Back Office Server (BOS) with web interface, track and locomotive simulators, and Edge Message Protocol (EMP) messaging subsystems. Development has begun with the intention of growing into an open-source PTC solution after experiencing first-hand the difficulties railroads are experiencing as they attempt to meet PTC implementation deadlines imposed by congress in 2008. It is a work in progress and distributable free under the MIT license. Images were obtained under the Creative Commons license.

PTC's mandate is to prevent:

* Train on train collisions
* Over-speed derailments
* Incursions into work zone limits
* Movement through misaligned track-switches
  
Interoperability between railroads is also required, as defined by the Federal Railroad Administration's Interoperable Train Control (ITC) standard.

PTC-Sim currently implements broker-assisted EMP communication between simulated on-track devices (locomotives and 220 MHz radio base-stations) and the BOS. Locomotive tracking and computer-aided-dispatch (CAD) is facilitated by a web interface, where current device status and location are displayed graphically.

## Usage

From a Linux terminal, start the application with `./PTCSim.py`, then navigate to http://localhost:5000/ptc_sim.
  
## Application Structure

### Components

Each component exists as a seperate entity. Any communication occuring between them happens via EMP messaging.

* **Back Office Server** : Provides CAD capabilities for communicating track restrictions to locomotives and displays real-time track device status and location via its website interface.

* **Message Broker**: An intermediate message translation system allowing bi-directional communication between track devices and the BOS.  Currently, each component transports EMP messages via TCP/IP only, but future versions may demonstrate Class C (IP based multicast protocol) and Class D (IP based point-to-point protocol) messaging.

* **Track Simulator**: Simulates a railroad and it's on-track devices:  
  * **Locomotives**:  Each locomotive travels along the track, broadcasting status messages and receiving CAD directives over its two 220 MHz radio transducers.
  * **220 MHz Radio Base Stations**: Receives locomotive status messages and transmits them to the Message Broker via LAN.
  * **Waysides**: Receives status messages from it's attached switches via LAN, then broadcasts them over 220 MHz radio to the BOS.
  * **Switches**: Each switch sends its current position (OPEN, CLOSED, or ERROR) to its parent wayside at regular intervals.

### Files

```
PTC-Sim
|   config.dat - Application configuration information.
|   lib_app.py - Shared application-level library.
|   lib_messaging.py - Messaging subsytem library.  
|   lib_track.py - Track simulation class library.
|   lib_web.py - Web specific library.
|   LICENSE - MIT License.
|   Procfile - Process definition, for use by hosted environments.
|   requirements.txt - pipenv dependencies file.
|   README.md - This document.
|   sim_bos.py - Starts the Back Office Server and sims, including web interface.
|
+---docs - Contains documentation files.
|
+---logs - Created on startup to hold log files for each component.
|
+---static - Static web content, such as images, css, and js.
|
+---templates - Flask web templates
|       home.html - 
|       layout.html - Top-level container template, including navbar.
|
+---track
|       track_bases.json - JSON representation of the track's radio base stations.
|       track_locos.json - JSON representation of the railroad's locomotives.
|       track_rail.json - JSON representation of the track's main branch.
```

### Unimplemented

At this point in development, some features typical in a PTC deployment, such as authentication, encryption, high availability, redundancy, persistent data, and connection session management are left unimplemented for the sake of demonstration simplicity. In addition, the track simulation is currently restricted to a single branch.

### Dependencies

Requires Python 2.7. All other dependencies are managed by the application, including Flask, Jinja, JavaScript, AJAX, jQuery, and the Google Maps API.

## # TODO

* Move js map ops to server-side
* Broker queue msg expire time
* Web Output: logs and broker queue monitor
  
* Allow other track models to be easily loaded via Google Earth
* Move JSON data to SQL
* Ensure PEP8 for file headers, imports, and docstrings (model after Tack and connection, but move public members to class level-doc)  
* Privatize necessary members and do validation on public members
* Readme screenshots and high-level PTC images
* Track Circuits, to aid col avoidance.