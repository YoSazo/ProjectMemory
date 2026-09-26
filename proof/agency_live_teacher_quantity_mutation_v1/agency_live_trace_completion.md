# Agency Live Quantity-Sequence Proof

- Teacher: `qwen2.5:32b`
- Teacher goal: `On DoorDash, find a cheese pizza from Pizza Hut in Dallas, Texas, select large with hand-tossed crust, set quantity to 2, and stop before adding it to the cart or checkout.`
- Student goal: ``
- Raw trace complete: `False`
- Bank trace complete: `False`
- Bank adapted packet sequence complete: `True`
- Required selected-term evidence complete: `True`
- Required quantity evidence complete: `True`
- Bank visible quantities: `[1, 2, 3, 3]`
- Bank terminal stop followed: `True`
- Teacher calls in student runs: `0`
- Transaction progression actions executed: `0`

The frozen teacher sequence grounds the item, visible quantity transition, required modifier dialog, and terminal boundary. This is one live quantity task and is not yet a broad quantity-transfer claim.
