# ASTM F3548-21 UTM USS time synchronization test scenario

## Overview

## Resources

### id_generator

A [resources.interuss.IDGeneratorResource](../../../resources/interuss/id_generator.py) that will be used to generate the IDs of the operational intent references created in this scenario.

### dss

A [resources.astm.f3548.v21.DSSInstanceResource](../../../resources/astm/f3548/v21/dss.py) with
which dummy operational intent references will be created.

### tested_uss

A [resources.flight_planning.FlightPlannerResource](../../../resources/flight_planning/flight_planners.py) for the USS under test

### flight_intents

TODO

## Setup test case

### [Ensure clean workspace](./dss/clean_workspace.md) test step

This step ensures that the identifiers used for this scenario are free and don't point to existing entities.

#### 🛑 Operational intent can be removed from the USS check

If a USS is not allowing update notifications for operational intents, it failes to properly implement **[astm.f3548.v21.USS0105](../../../requirements/astm/f3548/v21.md)**.

## Attempt to plan something in the past test case
### Attempt to plan something in the past test step

#### [Plan](../../flight_planning/plan_flight_intent.md)

#### [Validate](./validate_shared_operational_intent.md)

#### 🛑 Create an operational intent on the DSS check

TODO

#### 🛑 Notify USS of operational intent with valid details check

TODO

## [Cleanup](./dss/clean_workspace.md)

#### 🛑 Operational intent can be removed from the USS check

If a USS is not allowing update notifications for operational intents, it failes to properly implement **[astm.f3548.v21.USS0105](../../../requirements/astm/f3548/v21.md)**.

