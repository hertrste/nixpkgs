# Build the driver via
# nix-build integrationTest.nix -A simpleTest.driver
#
# and then run with:
# LOGFILE_JUNIT="junit-report.xml" ./result/bin/nixos-test-driver
#
# This will result in following junit compatible xml report:
# <?xml version="1.0"?>
# <testsuites disabled="0" errors="0" failures="1" tests="3" time="0.0">
#   <testsuite disabled="0" errors="0" failures="1" name="my test suite" skipped="0" tests="3" time="0">
#     <testcase name="main">
#       <system-out>Machine state will be reset. To keep it, pass --keep-vm-state
# start vlan
# running vlan (pid 270877; ctl /tmp/vde1.ctl)
# (finished: start all VLans, in 0.00 seconds)
# deleting VM state directory /tmp/vm-state-machine
# if you want to keep the VM state, pass --keep-vm-state
# Test will time out and terminate in 3600 seconds
# starting vm
# QEMU running (pid 270879)
# Guest shell says: b'Spawning backdoor root shell...\n'
# connected to guest root shell
# (connecting took 5.70 seconds)
# (finished: waiting for the VM to finish booting, in 5.79 seconds)
# (finished: waiting for unit default.target, in 10.38 seconds)
# (finished: must succeed: echo between subtests, in 0.01 seconds)
# </system-out>
#     </testcase>
#     <testcase name="subtest1">
#       <system-out>(finished: must succeed: echo subtest1, in 0.01 seconds)
# </system-out>
#     </testcase>
#     <testcase name="subtest2">
#       <failure type="failure" message="Test Case failed"/>
#       <system-out>Test "subtest2" failed with error: "command `echo subtest2` unexpectedly succeeded"
# kill machine (pid 270879)
# (finished: cleanup, in 0.06 seconds)
# </system-out>
#       <system-err>Test "subtest2" failed with error: "command `echo subtest2` unexpectedly succeeded"
# </system-err>
#     </testcase>
#   </testsuite>
# </testsuites>
{  }:
let
  pkgs = import ./. {};
in
{
  simpleTest = pkgs.nixosTest {
    name = "Simple Test";

    nodes.machine =  { pkgs, ...}:
    {

    };

    skipLint = true;
    skipTypeCheck = true;

    testScript = attrs: ''
      machine.wait_for_unit("default.target")

      with subtest("subtest1"):
        machine.succeed("echo subtest1")

      machine.succeed("echo between subtests")

      with subtest("subtest2"):
        machine.fail("echo subtest2")

      with subtest("subtest3"):
        machine.succeed("echo subtest3")
    '';
  };
}
