# PTC-Sim Implementation-Specific Message Specification

Adheres to EMP V4 (specified in S-9354.pdf) and uses fixed-format messages with variable-length header sections. The application-specific messaging implementation is defined as follows:

## EMP Fields

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

## Fixed-Format Messages

### 6000

Locomotive Status Message - Contains a single key/value data element of the form: 

```
    { sent      : (int) Unix time,
      locoID    : (str) Unique locomotive ID,
      speed     : (float) Current speed,
      heading   : (float) Current Heading,
      direction : (str) 'increasing' or 'decreasing',
      milepost  : (float) Nearest milepost ID,
      lat       : (float) Current GPS latitude in decimal degrees
      long      : (float) Current GPS longitude in decimal degrees
      bpp       : (float) Current Brake Pipe Pressure,
      conns     : (str) Key/Value pairs string of the form { CONNECTION_LABEL: BASEID } 
      bases     : (list) All receiving base station IDs
     }
```

### 6001

Wayside Status Msgs - Contains a single key/value data element of the form:

```
    { sent      : (int) Unix time,
      ID        : (str) Unique wayside ID,
      Children  : (str) Key/value pairs string of the form { ID: Status }
    }
```

**6002**: CAD to Locomotive Message - Contains a single key/value data element of the form:

```
    { sent      : (int) Unix time,
      ID        : (str) Intended recipient ID,
      Restrict  : (list) A list of restricted milepost ranges, as points
      }
```