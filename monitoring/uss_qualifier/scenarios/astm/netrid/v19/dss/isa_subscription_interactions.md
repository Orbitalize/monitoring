# ASTM NetRID DSS: ISA Subscription Interactions test scenario

## Overview

Verifies that interactions between ISAs and subscriptions happen as expected.

## Resources

### dss

[`DSSInstanceResource`](../../../../../resources/astm/f3411/dss.py) to be tested in this scenario.

### id_generator

[`IDGeneratorResource`](../../../../../resources/interuss/id_generator.py) providing the ISA ID for this scenario.

### isa

[`ServiceAreaResource`](../../../../../resources/netrid/service_area.py) describing an ISA to be created.

## Setup test case

### Ensure clean workspace test step

This scenario creates an ISA with a known ID. This step ensures that the ISA does not exist when the main part of the test starts.

Any previously created subscriptions for the test ISA's area that might still exist will be deleted.

#### Successful ISA query check

**[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** requires the implementation of the DSS endpoint enabling retrieval of information about a specific ISA; if the individual ISA cannot be retrieved and the error isn't a 404, then this requirement isn't met.

#### Removed pre-existing ISA check

If an ISA with the intended ID is already present in the DSS, it needs to be removed before proceeding with the test.  If that ISA cannot be deleted, then the **[astm.f3411.v19.DSS0030,d](../../../../../requirements/astm/f3411/v19.md)** requirement to implement the ISA deletion endpoint might not be met.

#### Notified subscriber check

When a pre-existing ISA needs to be deleted to ensure a clean workspace, any subscribers to ISAs in that area must be notified (as specified by the DSS).  If a notification cannot be delivered, then the **[astm.f3411.v19.NET0730](../../../../../requirements/astm/f3411/v19.md)** requirement to implement the POST ISAs endpoint isn't met.

#### Successful subscription query check

**[astm.f3411.v19.DSS0030,f](../../../../../requirements/astm/f3411/v19.md)** requires the implementation of the DSS endpoint to allow callers to retrieve the subscriptions they created.

#### Successful subscription deletion check

**[astm.f3411.v19.DSS0030,d](../../../../../requirements/astm/f3411/v19.md)** requires the implementation of the DSS endpoint to allow callers to delete subscriptions they created.

## ISA Subscription Interactions test case

### ISA Subscription Interactions test step

#### Create an ISA check

If the ISA cannot be created, the PUT DSS endpoint in **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)** is likely not implemented correctly.

#### Create a subscription within the ISA footprint check

The DSS should allow the creation of a subscription within the ISA footprint, otherwise it is in violation of **[astm.f3411.v19.DSS0030,c](../../../../../requirements/astm/f3411/v19.md)**

#### Subscription for the ISA's area mentions the ISA check

A subscription that is created for a volume that intersects with the previously created ISA should mention
the previously created ISA. If not, the serving DSS is in violation of **[astm.f3411.v19.DSS0030,c](../../../../../requirements/astm/f3411/v19.md)**.

#### Response to the mutation of the ISA contains subscription ID check

When an ISA is mutated, the DSS must return the identifiers for any subscription that was made to the ISA,
or be in violation of **[astm.f3411.v19.DSS0030,a](../../../../../requirements/astm/f3411/v19.md)**.

#### Response to the deletion of the ISA contains subscription ID check

When an ISA is deleted, the DSS must return the identifiers for any subscription that was made to the ISA,
or be in violation of **[astm.f3411.v19.DSS0030,b](../../../../../requirements/astm/f3411/v19.md)**.

#### Successful subscription deletion check

**[astm.f3411.v19.DSS0030,d](../../../../../requirements/astm/f3411/v19.md)** requires the implementation of the DSS endpoint to allow callers to delete subscriptions they created.

#### Notified subscriber check

Notifications to any subscriber to the created ISA need to be successful.  If a notification cannot be delivered, then the **[astm.f3411.v19.NET0730](../../../../../requirements/astm/f3411/v19.md)** requirement to implement the POST ISAs endpoint isn't met.

## Cleanup

The cleanup phase of this test scenario attempts to remove the ISA if the test ended prematurely while
also deleting any subscription it might have created for the ISA's area.

#### Successful ISA query check

**[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** requires the implementation of the DSS endpoint enabling retrieval of information about a specific ISA; if the individual ISA cannot be retrieved and the error isn't a 404, then this requirement isn't met.

#### Removed pre-existing ISA check

If an ISA with the intended ID is already present in the DSS, it needs to be removed before proceeding with the test.  If that ISA cannot be deleted, then the **[astm.f3411.v19.DSS0030,d](../../../../../requirements/astm/f3411/v19.md)** requirement to implement the ISA deletion endpoint might not be met.

#### Notified subscriber check

When a pre-existing ISA needs to be deleted to ensure a clean workspace, any subscribers to ISAs in that area must be notified (as specified by the DSS).  If a notification cannot be delivered, then the **[astm.f3411.v19.NET0730](../../../../../requirements/astm/f3411/v19.md)** requirement to implement the POST ISAs endpoint isn't met.

#### Successful subscription query check

**[astm.f3411.v19.DSS0030,f](../../../../../requirements/astm/f3411/v19.md)** requires the implementation of the DSS endpoint to allow callers to retrieve the subscriptions they created.

#### Successful subscription deletion check

**[astm.f3411.v19.DSS0030,d](../../../../../requirements/astm/f3411/v19.md)** requires the implementation of the DSS endpoint to allow callers to delete subscriptions they created.
