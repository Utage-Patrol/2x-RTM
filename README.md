# 2x-RTM

![Imgur](http://i.imgur.com/j7ATViE.jpeg)

# How does this work?
In order to create custom-sized characters in Arma 3, you need to resize both your mesh, and the RTM files. There are nearly 5,700 RTM files contained in around 700 folders for the arma 3 man. As such, scaling them manually simply isn't feasible if you want to make special units of varying heights. This handy little python script will process all RTMs in the debinarized_rtms folder (including subfolders), scale them to the specified size, then move them to the output folder, keeping the folder structure if there was any.

# How do I use this?
1. Download the ![latest release](https://github.com/Utage-Patrol/2x-RTM/releases)
2. Place debinarized RTMs in the "debinarized_rtms" folder (folder structure will be kept, so you can also place entire folders here, e.g. anims_f)
3. Edit the scale value in 2x-RTM.py to your desired size. 1.0 represents default arma man proportions. You can scale up or down
4. Run 2x-RTM.py
5. All RTM files will be scaled to your specifized size and moved to the "output" folder

   *Trying to scale binarized RTMs will show an error, please be sure to debinarize them first
