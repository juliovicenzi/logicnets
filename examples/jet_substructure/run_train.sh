#!/bin/bash
# python -u train.py --arch $1 --log-dir ./$1/ |& tee log/train_$1_"$(date +%y%m%d_%H%M%S)".txt

python -m cProfile -o log/"profile_$1_train_$(date +%y%m%d_%H%M%S).txt" --arch "$1" --log-dir ./"$1"/ |&
tee log/"outlog_syn_$1_$(date +%y%m%d_%H%M%S).txt"