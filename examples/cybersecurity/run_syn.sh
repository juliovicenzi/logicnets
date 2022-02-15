python -u neq2lut.py --arch nid-s --checkpoint nid_s/best_accuracy.pth --log-dir nid_s/verilog --add-registers --simulate-post-synthesis |& tee outlog$(date +%y%m%d_%H%M%S).txt

