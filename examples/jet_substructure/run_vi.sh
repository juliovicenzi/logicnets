#!/bin/sh
PART="${2:-"xc7z012sclg485-2"}"
echo $PART
python -m cProfile -o "log/vivado_syn_$(date +%y%m%d_%H%M%S).txt" syn.py --log-dir jsc-l/verilog --fpga-part "$PART" |& tee log/outlog_syn_$(date +%y%m%d_%H%M%S).txt
