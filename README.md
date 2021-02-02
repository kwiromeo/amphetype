
# Amphetype: Resurrected

Amphetype is an advanced typing practice program.

It gives the basic statistics like WPM (words per minute) and
accuracy, as well as identifies the keys/trigrams/words that break up
your flow, and what an impact these "viscous" combinations have on
your typing speed overall.

Features include:

* Entirely and deliberatly layout-agnostic.

  Amphetype doesn't care _what_ keyboard or layout you use, it only
  looks at _how_ you use it. As such it's likely not suitable for
  complete typing beginners who need an on-screen keyboard.

* Type your favorite novel!

  One of the ideas behind Amphetype was to not just use boring "stock
  texts," but to allow me to type texts I actually want to read as well.
  So a core feature is the ability to import whole novels (for example
  from [Project Gutenberg](https://www.gutenberg.org/)) and have
  Amphetype automatically generate bite-sized lessons from the text.
  When I was learning the [Colemak](https://colemak.com/) keyboard
  layout, I typed (and thus read) the entire _Metamorphosis_ by Franz
  Kafka!
  
* Generate lessons from past statistics.

  Amphetype features an advanced lesson generator where you can
  generate texts based on your past performance. Generate blocks of
  text to target practice your slowest words, trigrams, or keys!

* Highly customizable with regard to look and feel.

# Installing

**TODO**

I'll make actual installation packages. For now, the hard way:

Install dependencies:
``` bash
$ pip install translitcodec PyQt5
```

Run:

``` bash
$ python Amphetype.py
```

# Resurrected?

Yes, I originally made this program 12 years ago
[here](https://code.google.com/archive/p/amphetype/). I've updated it
somewhat, included some features that were requested back then, and
upgraded the code to use Python 3 and Qt5 (instead of Python 2 and
Qt4).

# Other Links

Review of (old) Amphetype: https://forum.colemak.com/topic/2201-training-with-amphetype/

My own inspiration for switching to a different keyboard layout:

* http://steve-yegge.blogspot.com/2008/09/programmings-dirtiest-little-secret.html

* https://blog.codinghorror.com/we-are-typists-first-programmers-second/

* https://www.ryanheise.com/colemak/

# Screenshots

**TODO**.

Using various themes:

![screenshot1](screenshot-typer.png)
![screenshot1](screenshot-pref.png)
![screenshot1](screenshot-graph.png)
![screenshot1](screenshot5.png)
