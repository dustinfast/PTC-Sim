# loco_sim

This application is a work in progress based on my experience in Postive Train Control. It demonstrates communication between active locomotives and a Back Office Server (BOS) and consists of three top-level parts:
  
**Locomotive Simulator**  
A simulated locomotive traveling on a track (as modeled by `track_rail.json`). As the loco travels, it connects to the radio base stations specified in `track_bases.json` for the purpose of communicating it's status (location, speed, etc.) to the BOS. If a base station is not available, the locomotive's status is enqued locally and sent at the next available opportunity.
The locomotive also monitors it's own queue in the messaging subsystem in order to receive commands (reduce speed, change direction, etc.) from the BOS.

Note: Multiple instances of the locomitive simulator may instantiated - each will give a simulated locomotive with a unique ID.

**Messaging Subsystem**  
Allows bi-directional communication between locomotives and the BOS by acting as a broker - messages from locomotives are enqued for receipt by the BOS, and messages to locomotives are enqued for the locomotive with the specified ID.

**Back Office Server**  
The BOS monitors the messaging subsystem and displays locomotive status graphically via its website and GoogleEarth. Additionally, the simulated locomotive may be controlled from the BOS.

## File Description

**sim_conf.dat** - Configuration information. For example, the message broker hostname/IP address.
**sim_bos.py** - The Back Office Server, or "BOS" (pronounced like "boss").
**sim_broker.py** - The QPID message broker.  
**sim_lib.py** - Shared classes and helper functions.
**sim_loco.py** - The locomotive simulator.  
**track_bases.json** - Specifies the base stations providing radio communication for sections of the track. Each base station consists of a unique ID and the on-track mileposts it provides coverage for. Gaps in coverage area allowed, as are areas of overlapping coverage.  
**track_rail.json** - A representation of a railroad track. Contains milepost markers and associated lat/long coordinates (in decimal degrees) of each.

## Usage

From a terminal, start the BOS with `./sim_bos.py`, then navigate to http://localhost/loco_sim.

