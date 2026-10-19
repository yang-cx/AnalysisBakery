# TRExFitter Ntuple Autobin Fit

This task trains agents to run the official ntuple-based TRExFitter example:

- localize `NtuplePaths` from EOS to a mounted mirror,
- remove the pinned-image-incompatible `LoggingFormat` setting,
- run ntuple reading with `trex-fitter n`,
- run automatic binning with `trex-fitter b`,
- build a RooStats workspace and run a fit.

Run the oracle locally with:

```bash
harbor run -p tasks/trexfitter-ntuple-autobin-fit -a oracle
```
