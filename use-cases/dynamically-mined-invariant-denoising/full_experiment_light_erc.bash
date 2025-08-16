#!/bin/bash

# Clear the contents of ./sok.json
> ./erc20.json

# Remove all files in ./output_light/sok and its subdirectories
find ./output_light/erc20 -type f -delete

# Run the reader.py script with each invariant JSON file


python reader.py ./invariants/erc20/0x1600c2e08acb830f2a4ee4d34b48594dade48651-TurexToken.inv.json ./output_light/erc20
python reader.py ./invariants/erc20/0x1fee5588cb1de19c70b6ad5399152d8c643fae7b-PhunToken.inv.json ./output_light/erc20
python reader.py ./invariants/erc20/0x28e57c27368d1475a3ce49a25c48c40b85e7f7e1-TetherUS.inv.json ./output_light/erc20
python reader.py ./invariants/erc20/0x37a15c92e67686aa268df03d4c881a76340907e8-PIXIUFINANCE.inv.json ./output_light/erc20
python reader.py ./invariants/erc20/0x3b2833cd4cfce20c04d0279ccbb8cd827c8bcdbf-Soya.inv.json ./output_light/erc20
python reader.py ./invariants/erc20/0x4d5d3170f407cacaaa328660c2ee2499055e3b07-Token.inv.json ./output_light/erc20
python reader.py ./invariants/erc20/0x6f2a550259532f7429530dcb93d86269629e3f2a-CloudProtocol.inv.json ./output_light/erc20
python reader.py ./invariants/erc20/0x8b68591fe802585a9713bd6ebe75d6c285236c54-DOGEVIPER.inv.json ./output_light/erc20
python reader.py ./invariants/erc20/0x923f3fe77732ec3fc5327eb52327b06be4e472f8-KPopKorea.inv.json ./output_light/erc20
python reader.py ./invariants/erc20/0x9fdbdd708b6f7247d57e9281e2073d2b88a67a42-FXCO.inv.json ./output_light/erc20
python reader.py ./invariants/erc20/0xb2923909b5d8bbe01505121f15a4503b6617dae7-WrappedHeC.inv.json ./output_light/erc20
python reader.py ./invariants/erc20/0xbc7d4fb8595f4b923ec53533f4bbd641c1910aca-YakuzaInu.inv.json ./output_light/erc20
python reader.py ./invariants/erc20/0xc382e04099a435439725bb40647e2b32dc136806-Cogecoin.inv.json ./output_light/erc20
python reader.py ./invariants/erc20/0xcc494c97a5d4374ec35bda83570c461c6d6f6079-DFV.inv.json ./output_light/erc20
python reader.py ./invariants/erc20/0xce90d1d98b5ca16b79c7eedada2454c2564da59e-TokenMintERC20MintableToken.inv.json ./output_light/erc20
python reader.py ./invariants/erc20/0xd4ac90e33ac839c29a3d98c807eeef0c4508bee8-YCCToken.inv.json ./output_light/erc20
python reader.py ./invariants/erc20/0xeeb690a0c9958e5375eda5694e754b125a6c972c-EnergyEfficientBitcoin.inv.json ./output_light/erc20
python reader.py ./invariants/erc20/0xf61ae54b74a37be4fc11e9f1a35021848d996afc-EmaxClassic.inv.json ./output_light/erc20
