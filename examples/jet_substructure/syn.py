#  Copyright (C) 2021 Xilinx, Inc
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os
from argparse import ArgumentParser

import torch
from torch.utils.data import DataLoader

from logicnets.nn import generate_truth_tables, \
    lut_inference, \
    module_list_to_verilog_module

from train import configs, model_config, dataset_config, test
from dataset import JetSubstructureDataset
from models import JetSubstructureNeqModel, JetSubstructureLutModel
from logicnets.synthesis import synthesize_and_get_resource_counts
from logicnets.util import proc_postsynth_file


if __name__ == "__main__":
    parser = ArgumentParser(description="Synthesize convert a PyTorch trained model into verilog")
    parser.add_argument('--fpga-part', type=str, default="xcu280-fsvh2892-2L-e",
                        help="FPGA synthesis part (default: %(default)s)")
    parser.add_argument('--clock-period', type=float, default=1.0,
                        help="Target clock frequency to use during Vivado synthesis (default: %(default)s)")
    parser.add_argument('--log-dir', type=str, default='./log',
                        help="A location to store the log output of the training run and the output model (default: %(default)s)")
    
    args = parser.parse_args()

    if not os.path.exists(args.log_dir):
        print(f"Could not find log directory {args.log_dir}")
        exit(-1)

    print("Running out-of-context synthesis")
    ret = synthesize_and_get_resource_counts(
        args.log_dir,
        "logicnet",
        fpga_part=args.fpga_part,
        clk_period_ns=args.clock_period,
        post_synthesis=1)
