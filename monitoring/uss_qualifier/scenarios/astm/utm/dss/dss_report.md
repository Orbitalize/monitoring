# ASTM SCD DSS: DSS Report Endpoint test scenario

## Overview

Attempts to interact with the DSS report endpoint to verify that it is available.

## Resources

### dss

[`DSSInstanceResource`](../../../../resources/astm/f3548/v21/dss.py) to be tested in this scenario.

## DSS Report Endpoint test case

### DSS Report Endpoint test step

#### 🛑 DSS report can be submitted check

If a properly formatted DSS report cannot be submitted to the DSS through the OpenAPI-specified endpoint,
the DSS is in violation of **[astm.f3548.v21.DSS0100,2](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 DSS report response format corresponds to spec check

If the response obtained from the DSS after submitting a report does not conform to the OpenAPI specification for the DSS reporting endpoint,
the DSS is in violation of **[astm.f3548.v21.DSS0100,2](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Report ID is populated by the DSS check

If a DSS to which a report was submitted does not return a report with a populated report ID,
it is failing to conform the OpenAPI specification for the DSS reporting endpoint, and therefore
in violation of **[astm.f3548.v21.DSS0100,2](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 DSS report response content is equal to what was sent check

If the response obtained from the DSS after submitting a report is not identical to what was submitted (except for the report ID)
the DSS is in violation of **[astm.f3548.v21.DSS0100,2](../../../../requirements/astm/f3548/v21.md)**.
