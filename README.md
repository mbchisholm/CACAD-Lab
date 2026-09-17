# CACAD-Lab
This is a playground for my various experiments in the world of Computer-Aided Computer-Aided Design (lol).

## About Build123d

Build123d is a Python-based, parametric (BREP) modeling framework for both 2D and 3D. It provides a python-based interface for working with Open Cascade's geometric kernel. For example:
![placeholder_img_box1.png]
![placeholder_img_box2.png]

I would check out the rest of these examples to get a better understanding of how this works. https://build123d.readthedocs.io/en/latest/introductory_examples.html

Parts can be exported to FreeCAD or the like. This makes it a lot easier to prompt an agent and end up with usable, exportable, parameterizable parts for 3D printing or CNC machining. While it certainly doesn't replace the traditional CAD experience and is especially limited when it comes to complex constraint geometry & assemblies, build123d has allowed me to build several handy widgets already. This repo is a collection of tools I've built for using build123d in a way that's practical and (hopefully) time-saving. 

Beyond anything practical, I really find this idea of agent-driven customizable 3D modeling interesting and have enjoyed messing around with it. The experience has also driven home for me the necessity of learning how to actually use the CAD tools the way they were intended to be used. 

### How I'm Using Build123d
(placeholder for the local work)

## FreeCAD
(placeholder for the local work)

## Projects In The Repo

1. Parametric standoffs
2. Customizable mounting plates for circuit boards
3. Parametric Cable Glands

## Resources

PARTCAD: A very useful collection of parts & assemblies https://partcad.org/repository

BD Warehouse: Generates special types of parametric parts that work with build123d https://bd-warehouse.readthedocs.io/en/latest/index.html
  - fastener - Nuts, Screws, Washers and custom holes
  - flange - Standardized parametric flanges
  - pipe - Standardized parametric pipes
  - thread - Parametric helical threads (Iso, Acme, Plastic, etc.)
