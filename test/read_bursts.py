import apreshttp
import apyres
import numpy as np
import matplotlib.pyplot as plt
import tempfile

tmp_dir = tempfile.TemporaryDirectory()

apres = apreshttp.API("http://192.168.1.1")
apres.setKey("18052021")

burst_data = []
data = []

for k in range(10):

    apres.radar.burst()
    results = apres.radar.results()

    print("Finished burst, got results with filename {:s}".format(results.filename))

    print("Downloading to {:s}".format(tmp_dir.name))
    saved_to = apres.data.download(results.filename, tmp_dir.name);

    burst_data.append(apyres.read(saved_to, skip_burst=False))
    plt.show()

    rp = apyres.RangeProfile.calculate_from_chirp([], burst_data[k].chirp_voltage, burst_data[k].fmcw_parameters)

    if len(data) == 0:
        data = rp
    else:
        data = np.vstack((data, rp));

    plt.imshow(np.abs(data.transpose()),aspect='auto')
    plt.show()


print("Finished")