#!/bin/bash
# python -u neq2lut.py --arch $1 --checkpoint $1/best_accuracy.pth --log-dir $1/verilog --add-registers |& 
# tee log/"outlog_syn_$1_$(date +%y%m%d_%H%M%S).txt"

python -m cProfile -o log/"profile_$1_$(date +%y%m%d_%H%M%S).txt" neq2lut.py--arch "$1" --checkpoint "$1"/best_accuracy.pth --log-dir "$1"/verilog --add-registers |& 
tee log/"outlog_syn_$1_$(date +%y%m%d_%H%M%S).txt"
