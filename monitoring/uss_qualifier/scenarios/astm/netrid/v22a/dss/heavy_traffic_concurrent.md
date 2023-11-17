# ASTM NetRID DSS: Concurrent Requests test scenario

## Overview

Create, query and delete ISAs on the DSS, concurrently.

## Resources

### dss

[`DSSInstanceResource`](../../../../../resources/astm/f3411/dss.py) to be tested in this scenario.

### id_generator

[`IDGeneratorResource`](../../../../../resources/interuss/id_generator.py) providing the ISA ID for this scenario.

### isa

[`ServiceAreaResource`](../../../../../resources/netrid/service_area.py) describing the ISAs to be created. All created ISAs use the same parameters.

## Setup test case

### Ensure clean workspace test step

This scenario creates ISA's with known IDs. This step ensures that no ISA with a known ID is present in the DSS before proceeding with the test.

#### Successful ISA query check

While F3411-19 does not explicitly require the implementation of a specific ISA retrieval endpoint, Annex A4 specifies the explicit format for this endpoint. If this format is not followed and the error isn't a 404, this check will fail per **[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

#### Removed pre-existing ISA check

If an ISA with the intended ID is already present in the DSS, it needs to be removed before proceeding with the test. If that ISA cannot be deleted, then the **[astm.f3411.v22a.DSS0030,b](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the ISA deletion endpoint might not be met.

#### Notified subscriber check

When a pre-existing ISA needs to be deleted to ensure a clean workspace, any subscribers to ISAs in that area must be notified (as specified by the DSS).  If a notification cannot be delivered, then the **[astm.f3411.v22a.NET0730](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the POST ISAs endpoint isn't met.

## Concurrent Requests test case

This test case will:

1. Create ISAs concurrently
2. Query each ISA individually, but concurrently
3. Search for all ISAs in the area of the created ISAs (using a single request)
4. Delete the ISAs concurrently
5. Query each ISA individually, but concurrently
6. Search for all ISAs in the area of the deleted ISAs (using a single request)

### [Create ISA concurrently test step](test_steps/put_isa.md)

This step attempts to concurrently create multiple ISAs, as specified in this scenario's resource, at the configured DSS.

#### Concurrent ISAs creation check

If any of the concurrent ISA creation requests fail or leads to the creation of an incorrect ISA, the PUT DSS endpoint in **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)** is likely not implemented correctly.

### Get ISAs concurrently test step

This step attempts to concurrently retrieve the previously created ISAs from the DSS.

#### Successful Concurrent ISA query check

If any of the ISAs cannot be queried, the GET ISA DSS endpoint in **[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** is likely not implemented correctly.

#### ISA response format check

The API for **[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** specifies an explicit format that the DSS responses must follow. If the DSS response does not validate against this format, this check will fail.

#### ISA ID matches check

The DSS returns the ID of the ISA in the response body. If this ID does not match the ID in the resource path, **[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** was not implemented correctly and this check will fail.

#### ISA version format check

Because the ISA version must be used in URLs, it must be URL-safe even though the ASTM standards do not explicitly require this. If the indicated ISA version is not URL-safe, this check will fail.

#### ISA version matches check

The DSS returns the version of the ISA in the response body. If this version does not match the version that was returned after creation, and that no modification of the ISA occurred in the meantime, **[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** was not implemented correctly and this check will fail.

#### ISA start time matches check

The ISA creation request specified an exact start time slightly past now, so the DSS should have created an ISA starting at exactly that time. If the DSS response indicates the ISA start time is not this value, **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

#### ISA end time matches check

The ISA creation request specified an exact end time, so the DSS should have created an ISA ending at exactly that time. If the DSS response indicates the ISA end time is not this value, **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

#### ISA URL matches check

When the ISA is created, the DSS returns the URL of the ISA in the response body. If this URL does not match the URL requested, **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

### [Search Available ISAs test step](test_steps/search_isas.md)

This test step searches the area in which the ISAs were concurrently created, and expects to find all of them.

#### Successful ISAs search check

The ISA search parameters are valid, as such the search should be successful. If the request is not successful, this check will fail per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

#### Correct ISAs returned by search check

The ISA search parameters cover the resource ISA, as such the resource ISA that exists at the DSS should be returned by the search. If it is not returned, this check will fail.

#### ISA ID matches check

The DSS returns the ID of the ISA in the response body. If this ID does not match the ID in the resource path, **[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** was not implemented correctly and this check will fail.

#### ISA version matches check

The DSS returns the version of the ISA in the response body. If this version has changed without an update of the ISA, **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)** was not implemented correctly and this check will fail.

#### ISA version format check

Because the ISA version must be used in URLs, it must be URL-safe even though the ASTM standards do not explicitly require this. If the indicated ISA version is not URL-safe, this check will fail.

#### ISA start time matches check

The ISA creation request specified an exact start time slightly past now, so the DSS should have created an ISA starting at exactly that time. If the DSS response indicates the ISA start time is not this value, **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

#### ISA end time matches check

The ISA creation request specified an exact end time, so the DSS should have created an ISA ending at exactly that time. If the DSS response indicates the ISA end time is not this value, **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

#### ISA URL matches check

When the ISA is created, the DSS returns the URL of the ISA in the response body. If this URL does not match the URL requested, **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

### [Delete ISAs concurrently test step](test_steps/delete_isa.md)

This step attempts to concurrently delete the earlier created ISAs.

#### ISAs deletion query success check

If an ISA cannot be deleted, the PUT DSS endpoint in **[astm.f3411.v22a.DSS0030,b](../../../../../requirements/astm/f3411/v22a.md)** is likely not implemented correctly.

#### ISA version format check

Because the ISA version must be used in URLs, it must be URL-safe even though the ASTM standards do not explicitly require this. If the indicated ISA version is not URL-safe, this check will fail.

#### ISA start time matches check

The ISA creation request specified an exact start time slightly past now, so the DSS should have created an ISA starting at exactly that time. If the DSS response indicates the ISA start time is not this value, **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

#### ISA end time matches check

The ISA creation request specified an exact end time, so the DSS should have created an ISA ending at exactly that time. If the DSS response indicates the ISA end time is not this value, **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

#### ISA URL matches check

When the ISA is created, the DSS returns the URL of the ISA in the response body. If this URL does not match the URL requested, **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

### Access Deleted ISAs test step

This step attempts to concurrently access the previously deleted ISAs from the DSS.

#### ISAs not found check

The ISA fetch request was about a deleted ISA, as such the DSS should reject it with a 404 HTTP code. If the DSS responds successfully to this request, or if it rejected with an incorrect HTTP code, this check will fail as per **[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

### [Search Deleted ISAs test step](test_steps/search_isas.md)

This step issues a search for active ISAs in the area of the previously deleted ISAs from the DSS.

#### Successful ISAs search check

The ISA search parameters are valid, as such the search should be successful. If the request is not successful, this check will fail as per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

#### ISAs not returned by search check

The ISA search area parameter cover the resource ISA, but it has been previously deleted, as such the ISA should not be returned by the search. If it is returned, this check will fail as per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

## Cleanup

The cleanup phase of this test scenario attempts to remove any created ISA if the test ended prematurely.

### Successful ISA query check

**[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** requires the implementation of the DSS endpoint enabling retrieval of information about a specific ISA; if the individual ISA cannot be retrieved and the error isn't a 404, then this requirement isn't met.

### Removed pre-existing ISA check

If an ISA with the intended ID is still present in the DSS, it needs to be removed before exiting the test. If that ISA cannot be deleted, then the **[astm.f3411.v22a.DSS0030,b](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the ISA deletion endpoint might not be met.

### Notified subscriber check

When an ISA is deleted, subscribers must be notified. If a subscriber cannot be notified, that subscriber USS did not correctly implement "POST Identification Service Area" in **[astm.f3411.v22a.NET0730](../../../../../requirements/astm/f3411/v22a.md)**.
