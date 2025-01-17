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
from logicnets.synthesis import synthesize_and_get_resource_counts
from logicnets.util import proc_postsynth_file

from train import configs, model_config, dataset_config, test
from dataset import get_preqnt_dataset
from models import UnswNb15NeqModel, UnswNb15LutModel

other_options = {
    "cuda": None,
    "log_dir": None,
    "checkpoint": None,
    "generate_bench": False,
    "add_registers": False,
    "simulate_pre_synthesis_verilog": False,
    "simulate_post_synthesis_verilog": False,
}

if __name__ == "__main__":
    parser = ArgumentParser(
        description="Synthesize convert a PyTorch trained model into verilog")
    parser.add_argument('--arch', type=str, choices=configs.keys(), default="nid-s",
                        help="Specific the neural network model to use (default: %(default)s)")
    parser.add_argument('--batch-size', type=int, default=None, metavar='N',
                        help="Batch size for evaluation (default: %(default)s)")
    parser.add_argument('--input-bitwidth', type=int, default=None,
                        help="Bitwidth to use at the input (default: %(default)s)")
    parser.add_argument('--hidden-bitwidth', type=int, default=None,
                        help="Bitwidth to use for activations in hidden layers (default: %(default)s)")
    parser.add_argument('--output-bitwidth', type=int, default=None,
                        help="Bitwidth to use at the output (default: %(default)s)")
    parser.add_argument('--input-fanin', type=int, default=None,
                        help="Fanin to use at the input (default: %(default)s)")
    parser.add_argument('--hidden-fanin', type=int, default=None,
                        help="Fanin to use for the hidden layers (default: %(default)s)")
    parser.add_argument('--output-fanin', type=int, default=None,
                        help="Fanin to use at the output (default: %(default)s)")
    parser.add_argument('--hidden-layers', nargs='+', type=int, default=None,
                        help="A list of hidden layer neuron sizes (default: %(default)s)")
    parser.add_argument('--clock-period', type=float, default=1.0,
                        help="Target clock frequency to use during Vivado synthesis (default: %(default)s)")
    parser.add_argument('--dataset-split', type=str, default='test', choices=['train', 'test'],
                        help="Dataset to use for evaluation (default: %(default)s)")
    parser.add_argument('--dataset-file', type=str, default='data/unsw_nb15_binarized.npz',
                        help="The file to use as the dataset input (default: %(default)s)")
    parser.add_argument('--log-dir', type=str, default='./log',
                        help="A location to store the log output of the training run and the output model (default: %(default)s)")
    parser.add_argument('--checkpoint', type=str, required=True,
                        help="The checkpoint file which contains the model weights")
    parser.add_argument('--generate-bench', action='store_true', default=False,
                        help="Generate the truth table in BENCH format as well as verilog (default: %(default)s)")
    parser.add_argument('--dump-io', action='store_true', default=False,
                        help="Dump I/O to the verilog LUT to a text file in the log directory (default: %(default)s)")
    parser.add_argument('--add-registers', action='store_true', default=False,
                        help="Add registers between each layer in generated verilog (default: %(default)s)")
    parser.add_argument('--simulate-pre-synthesis-verilog', action='store_true', default=False,
                        help="Simulate the verilog generated by LogicNets (default: %(default)s)")
    parser.add_argument('--simulate-post-synthesis-verilog', action='store_true', default=False,
                        help="Simulate the post-synthesis verilog produced by vivado (default: %(default)s)")
    args = parser.parse_args()
    defaults = configs[args.arch]
    options = vars(args)
    del options['arch']
    config = {}
    for k in options.keys():
        # Override defaults, if specified.
        config[k] = options[k] if options[k] is not None else defaults[k]

    if not os.path.exists(config['log_dir']):
        os.makedirs(config['log_dir'])

    # Split up configuration options to be more understandable
    model_cfg = {}
    for k in model_config.keys():
        model_cfg[k] = config[k]
    dataset_cfg = {}
    for k in dataset_config.keys():
        dataset_cfg[k] = config[k]
    options_cfg = {}
    for k in other_options.keys():
        if k == 'cuda':
            continue
        options_cfg[k] = config[k]

    # Fetch the test set
    print("Fetching test set")
    dataset = {}
    dataset[args.dataset_split] = get_preqnt_dataset(
        dataset_cfg['dataset_file'], split=args.dataset_split)
    test_loader = DataLoader(dataset[args.dataset_split],
                             batch_size=config['batch_size'], shuffle=False)

    print("Instantiating model")
    # Instantiate the PyTorch model
    x, y = dataset[args.dataset_split][0]
    model_cfg['input_length'] = len(x)
    model_cfg['output_length'] = 1
    model = UnswNb15NeqModel(model_cfg)

    # Load the model weights
    print("Loading weights...")
    checkpoint = torch.load(options_cfg['checkpoint'], map_location='cpu')
    model.load_state_dict(checkpoint['model_dict'])

    # Test the PyTorch model
    print("Running inference on baseline model...")
    model.eval()
    baseline_accuracy = test(model, test_loader, cuda=False)
    print("Baseline accuracy: %f" % (baseline_accuracy))

    # Instantiate LUT-based model
    lut_model = UnswNb15LutModel(model_cfg)
    lut_model.load_state_dict(checkpoint['model_dict'])

    # Generate the truth tables in the LUT module
    print("Converting to NEQs to LUTs...")
    generate_truth_tables(lut_model, verbose=True)

    # Test the LUT-based model
    print("Running inference on LUT-based model...")
    lut_inference(lut_model)
    lut_model.eval()
    lut_accuracy = test(lut_model, test_loader, cuda=False)
    print("LUT-Based Model accuracy: %f" % (lut_accuracy))
    modelSave = {'model_dict': lut_model.state_dict(),
                 'test_accuracy': lut_accuracy}

    torch.save(modelSave, options_cfg["log_dir"] + "/lut_based_model.pth")

    print("Generating verilog in %s..." % (options_cfg["log_dir"]))
    module_list_to_verilog_module(lut_model.module_list, "logicnet",
                                  options_cfg["log_dir"], generate_bench=options_cfg["generate_bench"], add_registers=options_cfg["add_registers"])
    print("Top level entity stored at: %s/logicnet.v ..." %
          (options_cfg["log_dir"]))

    if args.dump_io:
        io_filename = options_cfg["log_dir"] + f"io_{args.dataset_split}.txt"
        with open(io_filename, 'w') as f:
            pass  # Create an empty file.
        print(f"Dumping verilog I/O to {io_filename}...")
    else:
        io_filename = None

    if args.simulate_pre_synthesis_verilog:
        print("Running inference simulation of Verilog-based model...")
        lut_model.verilog_inference(
            options_cfg["log_dir"], "logicnet.v", logfile=io_filename, add_registers=options_cfg["add_registers"])
        verilog_accuracy = test(lut_model, test_loader, cuda=False)
        print("Verilog-Based Model accuracy: %f" % (verilog_accuracy))

    print("Running out-of-context synthesis")
    ret = synthesize_and_get_resource_counts(
        options_cfg["log_dir"], "logicnet", fpga_part="xcu280-fsvh2892-2L-e", clk_period_ns=args.clock_period, post_synthesis=1)

    if args.simulate_post_synthesis_verilog:
        print("Running post-synthesis inference simulation of Verilog-based model...")
        proc_postsynth_file(options_cfg["log_dir"])
        lut_model.verilog_inference(
            options_cfg["log_dir"] + "/post_synth", "logicnet_post_synth.v", io_filename, add_registers=options_cfg["add_registers"])
        post_synth_accuracy = test(lut_model, test_loader, cuda=False)
        print("Post-synthesis Verilog-Based Model accuracy: %f" %
              (post_synth_accuracy))
