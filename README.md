# MqttSnake
An educational/experimental snake-like multiplayer game that uses mqtt
----------

How To Use This
---------------

1. Install the necessary libraries ```pygame``` and ```paho-mqtt``` if not done already. You can run ```pip install -r dependencies.txt``` for that.
   Note that you may want to do that in a virtualenv.
2. run ```python3 Snake.py``` to run the game in single player mode.
   To run it in multiplayer mode, run ```python3 Snake.py YOURNAME REMOTENAME```, while _YOURNAME_ and _REMOTENAME_ are - you guessed it- placeholders for any unique names.
   It only matters that your counterpart uses the same names in reverse order.
3. Use the arrow-keys on your keyboard to control the snake. Have fun.


TODOs
-----------
- Currently the complte remote snake positions are marshalled into json and unmarshalled at the remote player. This might be replacable with a more condensed protocol between the players.
For the initial development, it seemed to be the quick-and dirty solution to ensure consistency between the two players.
  
- The game currently uses the hard-wired public mqtt broker ```broker.emqx.io```, setting the broker via the commandline might be nice to have.

- The frame-rate is limited to reduce latency issues in the game. The original snake becomes faster though as the game progresses.


