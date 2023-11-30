# Grease Pencil 2D Morphs
Addon for Blender that uses Grease Pencil frames made by the user to make interpolated frames and a rig control to manipulate the frames in order to fake shape keys in up to two dimensions. Could be useful for rigs with head turns, muscle bulging, automatic jiggle physics, and probably more. In order to morph things that should be animated separately such as eyes and mouths, the addon also features bone morphing with the same controls.

Waiting on Grease Pencil shape keys 😴
### Initial Release Video
[![](https://markdown-videos.vercel.app/youtube/sTh96dmcoSk)](https://youtu.be/sTh96dmcoSk)
### Update 1.1 Video
[![](https://markdown-videos.vercel.app/youtube/NDgR_nXWbL0)](https://youtu.be/NDgR_nXWbL0)

### Interpolate Sequence Disorderly operator
The addon also comes with a custom Grease Pencil operator "Interpolate Sequence Disorderly" that does the same thing as Interpolate Sequence, but can handle interpolating between two frames that have different stroke orders. See the initial release video for limitations.

## Credits
Thanks to atticus-lv for [their node editor template](https://github.com/atticus-lv/simple_node_tree). It would have taken me a lot longer to implement my own node editor if I had to figure it all out myself.