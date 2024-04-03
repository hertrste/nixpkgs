# Build the driver via
# nix-build integrationTest.nix -A simpleTest.driver
#
# and then run with:
# LOGFILE="report.xml" ./result/bin/nixos-test-driver --junit-xml
#
# This will result in a junit compatible report.xml.
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

      # Following test fails. This leads to the abortion of the run and subtest3
      # will be skipped. The failing test here is mainly to show that the xml
      # report contains a failed test.
      with subtest("subtest2"):
        machine.fail("echo subtest2")

      with subtest("subtest3"):
        machine.succeed("echo subtest3")
    '';
  };
}
