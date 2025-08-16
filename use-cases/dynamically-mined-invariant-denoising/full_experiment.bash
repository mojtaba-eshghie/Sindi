#!/bin/bash

# Clear the contents of ./sok.json
> ./sok.json

# Remove all files in ./output/sok and its subdirectories
find ./output/sok -type f -delete

# Run the reader.py script with each invariant JSON file
python reader.py ./invariants/sok/0x3ec4a6cfe803ee84009ce6e1ecf419c9cb1e8af0-bVault.inv.json ./output/sok
python reader.py ./invariants/sok/0x6b7a87899490ece95443e979ca9485cbe7e71522-AnyswapV4Router.inv.json ./output/sok
python reader.py ./invariants/sok/0x39b1df026010b5aea781f90542ee19e900f2db15-Keep3rV2Oracle.inv.json ./output/sok
python reader.py ./invariants/sok/0x67b66c99d3eb37fa76aa3ed1ff33e8e39f0b9c7a-Bank.inv.json ./output/sok
python reader.py ./invariants/sok/0x818e6fecd516ecc3849daf6845e3ec868087b755-KyberNetworkProxy.inv.json ./output/sok
python reader.py ./invariants/sok/0x6684977bbed67e101bb80fc07fccfba655c0a64f-SushiMaker.inv.json ./output/sok
python reader.py ./invariants/sok/0x6847259b2b3a4c17e7c43c54409810af48ba5210-ControllerV4.inv.json ./output/sok
python reader.py ./invariants/sok/0x88093840aad42d2621e1a452bf5d7076ff804d61-UFragments.inv.json ./output/sok
python reader.py ./invariants/sok/0xacd43e627e64355f1861cec6d3a6688b31a6f952-yVault.inv.json ./output/sok
python reader.py ./invariants/sok/0xe11fc0b43ab98eb91e9836129d1ee7c3bc95df50-SushiMaker.inv.json ./output/sok
