# Ensure clean workspace test step fragment

This page describes the content of a common test step that ensures a clean workspace for testing interactions with a DSS

## 🛑 Operational intent references can be queried by ID check

If an existing operational intent reference cannot directly be queried by its ID, or if for a non-existing one the DSS replies with a status code different than 404,
the DSS implementation is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Operational intent references can be searched for check

A client with valid credentials should be allowed to search for operational intents in a given area.
Otherwise, the DSS is not in compliance with **[astm.f3548.v21.DSS0005,2](../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Operational intent reference removed check

If an existing operational intent cannot be deleted when providing the proper ID and OVN, the DSS implementation is in violation of
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Successful subscription search query check

**[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)** requires the implementation of the DSS endpoint to allow callers to retrieve the subscriptions they created.

## 🛑 Subscription can be queried by ID check

If the DSS cannot be queried for the existing test ID, the DSS is likely not implementing **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)** correctly.

## 🛑 Subscription can be deleted check

**[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)** requires the implementation of the DSS endpoint to allow callers to delete subscriptions they created.

## 🛑 Constraint references can be queried by ID check

If an existing constraint reference cannot directly be queried by its ID, or if for a non-existing one the DSS replies with a status code different than 404,
the DSS implementation is in violation of **[astm.f3548.v21.DSS0005,3](../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Constraint references can be searched for check

A client with valid credentials should be allowed to search for constraint references in a given area.
Otherwise, the DSS is not in compliance with **[astm.f3548.v21.DSS0005,4](../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Constraint reference removed check

If an existing constraint cannot be deleted by its manager when providing the proper ID and OVN, the DSS implementation is in violation of
**[astm.f3548.v21.DSS0005,3](../../../../requirements/astm/f3548/v21.md)**.
