# PTC-Sim - Positive Train Control Simulation

[![Heroku](https://heroku-badge.herokuapp.com/?app=heroku-badge)](https://ptc-sim.herokuapp.com/)

This application is a Positive Train Control (PTC) Back Office Server (BOS) with web interface, track/locomotive simulators, and Edge Message Protocol (EMP) messaging subsystems. Development has begun with the intention of growing into an open-source PTC solution after observing first-hand the difficulties railroads are currently experiencing as they attempt to meet PTC implementation deadlines imposed by congress. It is a work in progress and distributable free under the MIT license. All images obtained under the Creative Common License.

PTC's mandate is to prevent:

* Train on train collisions
* Over-speed derailments
* Incursions into work zone limits
* Movement through misaligned track-switches
  
Interoperability between railroads is also required, as defined by the Federal Railroad Administration's Interoperable Train Control (ITC) standard.

PTC-Sim currently implements broker-assisted EMP communication between simulated on-track devices (locomotives and 220 MHz radio base-stations) and the BOS. Locomotive tracking and computer-aided-dispatch (CAD) is facilitated by a web interface, where current device status and location are displayed graphically. For the simulation, each web client gets its own "sanbox", consisting of an independent broker and track/locomotive simulator.

## Usage

From a Linux terminal, start the application with `./sim_bos.py`, then navigate to 
  
## Application Structure

### Components

Each component exists as a seperate entity. Communication between entities occurs via EMP messaging over TCP/IP.

* **Back Office Server** : Displaying real-time device and locomotive status via its web interface. Plans exist to also provides CAD capabilities, such as communicating track restrictions to locomotives.

* **Message Broker**: An intermediate message translation system allowing bi-directional communication between track devices, locomotives, and the BOS. Currently, each component transports EMP messages via TCP/IP only. Future versions will implememnt Class C (IP based multicast protocol) and Class D (IP based point-to-point protocol) messaging.

* **Track Simulator**: Simulates on-track devices:  
  * **Locomotives**:  Each locomotive travels along the track, broadcasting status messages (and eventually receiving CAD directives) over its two simulated 220 MHz radio transducers.
  * **220 MHz Radio Base Stations**: Receives locomotive status messages and transmits them to the Message Broker via LAN.
  * **Waysides**: Receives status messages from it's attached switches via LAN, then broadcasts them over 220 MHz radio to the BOS.
  * **Switches**: Each switch sends its current position (OPEN, CLOSED, or ERROR) to its parent wayside at regular intervals.

### Files

```
PTC-Sim
|   app_config.dat - Application configuration information.
|   lib_app.py - Shared application-level library.
|   lib_messaging.py - Messaging subsystem library.  
|   lib_track.py - Track simulation class library.
|   lib_web.py - Web interface library.
|   LICENSE - MIT License.
|   Procfile - Process definition, for use in virtual environments.
|   requirements.txt - Dependencies, for use in virtual environments.
|   runtime.txt - Python version def, for use in virtual environments.
|   README.md - This document.
|   sim_bos.py - The Back Office Server / web interface.
|
+---docs - Contains documentation.
|
+---logs - Created on startup to hold log files for each component.
|
+---static - Static web content, such as images, css, and js.
|
+---templates - Flask web templates
|       home.html - The main device and locomotive satus page. 
|       layout.html - Top-level container template, including navbar.
|
+---track
|       track_bases.json - JSON representation of the track's radio base stations.
|       track_locos.json - JSON representation of the railroad's locomotives.
|       track_rail.json - JSON representation of the track's main branch.
```

### Dependencies / Technologies

Requires Python 2.7.
Other dependencies managed by the application include: Flask, Jinja, JQuery, and the GoogleMaps API.

### Preview

To preview PTC-Sim, navigate to https://ptc-sim.herokuapp.com/

![PTC-Sim Screenshot](https://github.com/dustinfast/PTC-Sim/raw/master/docs/scrnshot.png "PTC-Sim Screenshot")

### Unimplemented

At this point in development, some features typical in a PTC deployment, such as authentication, encryption, high availability, redundancy, and persistent data have not been implemented. The track simulation is also currently restricted to a single branch, and locomotives are not currently aware of each other on the track. Additionally, the following TODO items are in progress:

* Broker queue msg expire time
* Web Output: logs and broker queue monitor, to demonstrate msging system
* Base coverage overlays in website map display
* Segregated logs
* Ensure PEP8 for file headers, imports, and docstrings (model after Tack and connection, but move public members to class level-doc)  
* Privatize necessary members and do validation on public members
* Readme screenshots and high-level PTC images
* Track Circuits, to aid col avoidance.