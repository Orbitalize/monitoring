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

This scenario creates ISA's and subscriptions with known IDs. This step ensures that no ISA or subscription with a known ID is present in the DSS before proceeding with the test.

#### Search for all subscriptions in ISA area check

If a correct request for subscriptions in the parametrized ISA's area fails, the **[astm.f3411.v22a.DSS0030,f](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the GET Subscriptions endpoint is not met.

#### Subscription can be queried by ID check

If a subscription created by the client cannot be queried, the **[astm.f3411.v22a.DSS0030,e](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the GET Subscription endpoint is not met.

#### Subscription can be deleted check

If a subscription created by the client cannot be deleted, the **[astm.f3411.v22a.DSS0030,d](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the DELETE Subscription endpoint is not met.

#### Successful ISA query check

While F3411-19 does not explicitly require the implementation of a specific ISA retrieval endpoint, Annex A4 specifies the explicit format for this endpoint. If this format is not followed and the error isn't a 404, this check will fail per **[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

#### Removed pre-existing ISA check

If an ISA with the intended ID is already present in the DSS, it needs to be removed before proceeding with the test. If that ISA cannot be deleted, then the **[astm.f3411.v22a.DSS0030,b](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the ISA deletion endpoint might not be met.

#### Notified subscriber check

When a pre-existing ISA needs to be deleted to ensure a clean workspace, any subscribers to ISAs in that area must be notified (as specified by the DSS).  If a notification cannot be delivered, then the **[astm.f3411.v22a.NET0730](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the POST ISAs endpoint isn't met.

## Concurrent requests test case

This test case will:

TODO rewrite description once scenario is implemented

1. Create ISAs concurrently
2. Query each ISA individually, but concurrently
3. Search for all ISAs in the area of the created ISAs (using a single request)
4. Delete the ISAs concurrently
5. Query each ISA individually, but concurrently
6. Search for all ISAs in the area of the deleted ISAs (using a single request)

### [Create ISA concurrently test step](test_steps/put_isa.md)

This step attempts to concurrently create multiple ISAs, as specified in this scenario's resource, at the configured DSS.

#### Concurrent ISAs creation check

If any of the concurrent ISA creation requests fails or leads to the creation of an incorrect ISA, the PUT DSS endpoint in **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)** is likely not implemented correctly.

#### Concurrent subscriptions creation check

If any of the concurrent subscription creation requests fails or leads to the creation of an incorrect subscription, the PUT Subscription DSS endpoint in **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** is likely not implemented correctly.

#### Subscription response format check

The API for **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** specifies an explicit format that the DSS responses must follow.  If the DSS response does not validate against this format, this check will fail.

#### Subscription ID matches check

When the subscription is created, the DSS returns the ID of the subscription in the response body.  If this ID does not match the ID in the resource path, **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** was not implemented correctly and this check will fail.

#### Created ISAs mention subscriptions known to exist check

ISAs created *after* a subscription has been successfully created for the same area must contain the subscription ID, otherwise the DSS is in violation of **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)**.

#### Created subscriptions mention ISAs known to exist check

Subscriptions created *after* an ISA has been successfully created for the same area must contain the ISA ID, otherwise the DSS is in violation of **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)**.

#### Subscription start time matches check

The subscription creation request specified an exact start time slightly past now, so the DSS should have created a subscription starting at exactly that time. If the DSS response indicates the subscription start time is not this value, **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

#### Subscription end time matches check

The subscription creation request specified an exact end time, so the DSS should have created a subscription ending at exactly that time. If the DSS response indicates the subscription end time is not this value, **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

#### Subscription flights url matches check

The subscription creation request specified the base URL for the flights endpoint. If the DSS response does not contain the proper URL, **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

#### Subscription owner matches check

The DSS indicates in every returned subscription the identify of its owner. If this identity does not correspond to the one that is used by the USS qualifier to authenticate to the DSS,
the DSS is not implementing **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** correctly, and this check will fail.

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

### Get subscriptions concurrently test step

Verify that the created subscriptions exist and are as expected

#### Successful concurrent subscription queries check

If any of the concurrently run queries for the previously created subscription fails, the GET Subscription DSS endpoint in **[astm.f3411.v22a.DSS0030,e](../../../../../requirements/astm/f3411/v22a.md)** is likely not implemented correctly.

#### Subscription response format check

The API for **[astm.f3411.v22a.DSS0030,e](../../../../../requirements/astm/f3411/v22a.md)** specifies an explicit format that the DSS responses must follow.  If the DSS response does not validate against this format, this check will fail.

#### Subscription ID matches check

If the returned subscription ID does not match the ID requested in the resource path, **[astm.f3411.v22a.DSS0030,e](../../../../../requirements/astm/f3411/v22a.md)** was not implemented correctly and this check will fail.

#### Created ISAs mention subscriptions known to exist check

ISAs created *after* a subscription has been successfully created for the same area must contain the subscription ID, otherwise the DSS is in violation of **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)**.

#### Created subscriptions mention ISAs known to exist check

Subscriptions created *after* an ISA has been successfully created for the same area must contain the ISA ID, otherwise the DSS is in violation of **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)**.

#### Subscription start time matches check

The subscription creation request specified an exact start time slightly past now, so the DSS should have created a subscription starting at exactly that time. If the DSS response indicates the subscription start time is not this value, **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

#### Subscription end time matches check

The subscription creation request specified an exact end time, so the DSS should have created a subscription ending at exactly that time. If the DSS response indicates the subscription end time is not this value, **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

#### Subscription flights url matches check

The subscription creation request specified the base URL for the flights endpoint. If the DSS response does not contain the proper URL, **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

#### Subscription owner matches check

The DSS indicates in every returned subscription the identify of its owner. If this identity does not correspond to the one that is used by the USS qualifier to authenticate to the DSS,
the DSS is not implementing **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** correctly, and this check will fail.

#### Subscription version matches check

If the version of the subscription has changed without any update having been done, the DSS might not be implementing **[astm.f3411.v22a.DSS0030,e](../../../../../requirements/astm/f3411/v22a.md)** correctly, and this check will fail.

#### Notification indices incremented check

Subscriptions that exist when ISAs are created must have their notification index incremented for each new created or updated ISA that
overlaps with their defined area.

If after the creation or mutation of an ISA within the subscription's area the DSS does not increment the subscription's notification index, the DSS is in violation of **[astm.f3411.v22a.DSS0030,e](../../../../../requirements/astm/f3411/v22a.md)**,
and this check will fail.

### [Search available ISAs test step](test_steps/search_isas.md)

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

### Search subscriptions test step

Checks that created subscriptions are properly returned by the DSS's search endpoint

#### Successful subscriptions search check

The subscription search parameters are valid, as such the subscriptions search should be successful. If the request is not successful, this check will fail per **[astm.f3411.v22a.DSS0030,f](../../../../../requirements/astm/f3411/v22a.md)**.

#### Correct subscriptions returned by search check

The search request is expected to return all subscriptions created by the test. If it does not, the **[astm.f3411.v22a.DSS0030,f](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the GET Subscriptions endpoint is not met.

#### Subscriptions response format check

The API for **[astm.f3411.v22a.DSS0030,f](../../../../../requirements/astm/f3411/v22a.md)** specifies an explicit format that the DSS responses must follow.  If the DSS response does not validate against this format, this check will fail.

#### Subscription ID matches check

If the returned subscription ID does not match the ID requested in the resource path, **[astm.f3411.v22a.DSS0030,e](../../../../../requirements/astm/f3411/v22a.md)** was not implemented correctly and this check will fail.

#### Created ISAs mention subscriptions known to exist check

ISAs created *after* a subscription has been successfully created for the same area must contain the subscription ID, otherwise the DSS is in violation of **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)**.

#### Created subscriptions mention ISAs known to exist check

Subscriptions created *after* an ISA has been successfully created for the same area must contain the ISA ID, otherwise the DSS is in violation of **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)**.

#### Subscription start time matches check

The subscription creation request specified an exact start time slightly past now, so the DSS should have created a subscription starting at exactly that time. If the DSS response indicates the subscription start time is not this value, **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

#### Subscription end time matches check

The subscription creation request specified an exact end time, so the DSS should have created a subscription ending at exactly that time. If the DSS response indicates the subscription end time is not this value, **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

#### Subscription flights url matches check

The subscription creation request specified the base URL for the flights endpoint. If the DSS response does not contain the proper URL, **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

#### Subscription owner matches check

The DSS indicates in every returned subscription the identify of its owner. If this identity does not correspond to the one that is used by the USS qualifier to authenticate to the DSS,
the DSS is not implementing **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** correctly, and this check will fail.

#### Subscription version matches check

If the version of the subscription has changed without any update having been done, the DSS might not be implementing **[astm.f3411.v22a.DSS0030,f](../../../../../requirements/astm/f3411/v22a.md)** correctly, and this check will fail.

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

### Delete subscriptions concurrently test step

#### Subscriptions deletion query success check

If any of the concurrent deletion queries fails, the DELETE Subscription DSS endpoint in **[astm.f3411.v22a.DSS0030,d](../../../../../requirements/astm/f3411/v22a.md)** is likely not implemented correctly.

#### Delete subscription response format check

The API for **[astm.f3411.v22a.DSS0030,d](../../../../../requirements/astm/f3411/v22a.md)** specifies an explicit format that the DSS responses must follow.  If the DSS response does not validate against this format, this check will fail.

#### Subscription ID matches check

If the returned subscription ID does not match the ID requested in the deleted resource path, **[astm.f3411.v22a.DSS0030,d](../../../../../requirements/astm/f3411/v22a.md)** was not implemented correctly and this check will fail.

#### Created ISAs mention subscriptions known to exist check

ISAs created *after* a subscription has been successfully created for the same area must contain the subscription ID, otherwise the DSS is in violation of **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)**.

#### Created subscriptions mention ISAs known to exist check

Subscriptions created *after* an ISA has been successfully created for the same area must contain the ISA ID, otherwise the DSS is in violation of **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)**.

#### Subscription start time matches check

The subscription creation request specified an exact start time slightly past now, so the DSS should have created a subscription starting at exactly that time. If the DSS response indicates the subscription start time is not this value, **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

#### Subscription end time matches check

The subscription creation request specified an exact end time, so the DSS should have created a subscription ending at exactly that time. If the DSS response indicates the subscription end time is not this value, **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

#### Subscription flights url matches check

The subscription creation request specified the base URL for the flights endpoint. If the DSS response does not contain the proper URL, **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

#### Subscription owner matches check

The DSS indicates in every returned subscription the identify of its owner. If this identity does not correspond to the one that is used by the USS qualifier to authenticate to the DSS,
the DSS is not implementing **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** correctly, and this check will fail.

#### Created ISAs mention subscriptions known to exist check

ISAs created *after* a subscription has been successfully created for the same area must contain the subscription ID, otherwise the DSS is in violation of **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)**.

#### Created subscriptions mention ISAs known to exist check

Subscriptions created *after* an ISA has been successfully created for the same area must contain the ISA ID, otherwise the DSS is in violation of **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)**.

#### Subscription start time matches check

The subscription creation request specified an exact start time slightly past now, so the DSS should have created a subscription starting at exactly that time. If the DSS response indicates the subscription start time is not this value, **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

#### Subscription end time matches check

The subscription creation request specified an exact end time, so the DSS should have created a subscription ending at exactly that time. If the DSS response indicates the subscription end time is not this value, **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

#### Subscription flights url matches check

The subscription creation request specified the base URL for the flights endpoint. If the DSS response does not contain the proper URL, **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

#### Subscription owner matches check

The DSS indicates in every returned subscription the identify of its owner. If this identity does not correspond to the one that is used by the USS qualifier to authenticate to the DSS,
the DSS is not implementing **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)** correctly, and this check will fail.

#### Subscription version matches check

If the version of the subscription has changed without any update having been done, the DSS might not be implementing **[astm.f3411.v22a.DSS0030,e](../../../../../requirements/astm/f3411/v22a.md)** correctly, and this check will fail.

#### Notification indices incremented check

Subscriptions that exist when ISAs are deleted must have their notification index incremented for each deleted ISA.

If the subscription is then deleted, the DSS is expected to return the correct notification index in the response to the DELETE Subscription request.

If the DSS returns an incorrect notification index, it is not implementing **[astm.f3411.v22a.DSS0030,d](../../../../../requirements/astm/f3411/v22a.md)** properly, and this check will fail.

### Access deleted ISAs test step

This step attempts to concurrently access the previously deleted ISAs from the DSS.

#### ISAs not found check

The ISA fetch request was about a deleted ISA, as such the DSS should reject it with a 404 HTTP code. If the DSS responds successfully to this request, or if it rejected with an incorrect HTTP code, this check will fail as the DSS violates **[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

#### Subscriptions not found check

The subscription fetch request was about a deleted subscription, as such the DSS should reject it with a 404 HTTP code. If the DSS responds successfully to this request, or if it rejected with an incorrect HTTP code, this check will fail as the DSS violates **[astm.f3411.v22a.DSS0030,e](../../../../../requirements/astm/f3411/v22a.md)**.

### [Search deleted ISAs test step](test_steps/search_isas.md)

This step issues a search for active ISAs in the area of the previously deleted ISAs from the DSS.

#### Successful ISAs search check

The ISA search parameters are valid, as such the search should be successful. If the request is not successful, this check will fail as per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

#### ISAs not returned by search check

The ISA search area parameter cover the resource ISA, but it has been previously deleted, as such the ISA should not be returned by the search. If it is returned, this check will fail as per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

### Search deleted subscriptions test step

This check issues a search for subscriptions in the area of the previously deleted subscriptions.

#### Successful subscriptions search check

The subscription search parameters are valid, as such the search should be successful. If the request is not successful, this check will fail as per **[astm.f3411.v22a.DSS0030,f](../../../../../requirements/astm/f3411/v22a.md)**.

#### Subscriptions not returned by search check

The subscription search area covers the area for which previous subscriptions were created, but these have been deleted.
If any of the deleted subscriptions is present in the result, the DSS is not implementing **[astm.f3411.v22a.DSS0030,f](../../../../../requirements/astm/f3411/v22a.md)** properly.

## Cleanup

The cleanup phase of this test scenario attempts to remove any created ISA if the test ended prematurely.

### Successful ISA query check

**[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** requires the implementation of the DSS endpoint enabling retrieval of information about a specific ISA; if the individual ISA cannot be retrieved and the error isn't a 404, then this requirement isn't met.

### Removed pre-existing ISA check

If an ISA with the intended ID is still present in the DSS, it needs to be removed before exiting the test. If that ISA cannot be deleted, then the **[astm.f3411.v22a.DSS0030,b](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the ISA deletion endpoint might not be met.

### Notified subscriber check

When an ISA is deleted, subscribers must be notified. If a subscriber cannot be notified, that subscriber USS did not correctly implement "POST Identification Service Area" in **[astm.f3411.v22a.NET0730](../../../../../requirements/astm/f3411/v22a.md)**.

### Search for all subscriptions in ISA area check

If a correct request for subscriptions in the parametrized ISA's area fails, the **[astm.f3411.v22a.DSS0030,f](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the GET Subscriptions endpoint is not met.

### Subscription can be deleted check

If a subscription created by the client cannot be deleted, the **[astm.f3411.v22a.DSS0030,d](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the DELETE Subscription endpoint is not met.

### Subscription can be queried by ID check

If a subscription created by the client cannot be queried, the **[astm.f3411.v22a.DSS0030,e](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the GET Subscription endpoint is not met.
