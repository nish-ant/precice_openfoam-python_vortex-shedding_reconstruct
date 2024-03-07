## About
OpenFOAM case directory for simulating incompressible flow over a 2D cylinder placed near ground, $Re=200$.
The simulation generates snapshot data which will be stored in the `postProcessing/internalField` directory.
The parameters to control the snapshot generation are defined in `system/sampling/internalCloud`.

NOTE: Modify `./constant/transportProperties` to change the Reynolds number.

## Sequence of submitting slurm scripts
```sh
sbatch runscript.preprocess         #- meshing
sbatch runscript.solve.1            #- initial run till periodic vortex shedding
sbatch runscript.solve.2            #- restart run for snapshot generation
sbatch runscript.splitProbe2TimeDir #- split snapshot file into time directories
```

## Optional
```sh
gnuplot plot_ClCd.p                 #- plot lift and drag coefficients
```