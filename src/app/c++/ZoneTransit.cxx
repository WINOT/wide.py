/****************************************************************************
 *  Librairie:    LibZoneTransit                                            *
 *  Auteur:       Mariane Maynard                                           *
 *  Description:  Construction de la librairie boost python de la classe    *
 *                ZoneTransit, Modification et Fichier                      *
 ****************************************************************************/

#include <boost/python.hpp>
#include <boost/python/suite/indexing/vector_indexing_suite.hpp>
#include <boost/python/overloads.hpp>
#include "ZoneTransit.h"
#include "SFichier.h"
#include "Fichier.h"
#include "Ajout.h"
#include "Suppression.h"
#include <string>
#include "Types.h"

using namespace boost::python;
using std::string;
using boost::shared_ptr;
using namespace types;

BOOST_PYTHON_MODULE(libZoneTransit)
{
  void (ZoneTransit::*add1)(const vector<ModificationPtr>& pm) = &ZoneTransit::add;
  void (ZoneTransit::*add2)(const ModificationPtr& m)          = &ZoneTransit::add;

  //Definit la classe Fichier. Fichier est un alias pour FichierType<string>
  class_<Fichier, boost::noncopyable>("File")
    .def(init<const string &>())
    .def("writeToDisk", &Fichier::ecrireSurDisque)
    .def("insert", &Fichier::inserer)
    .def("delete", &Fichier::supprimer)
    .def("printContent", &Fichier::printContenu)
    .add_property("content", &Fichier::getContenu);

  class_<ZoneTransit, boost::noncopyable>("TransitZone")
    .def(init<const string&>())
    .def("add", add1)
    .def("add", add2)
    .def("writeModifications", &ZoneTransit::ecrireModifications)
    .def("isEmpty", &ZoneTransit::estVide)
    .add_property("content", &ZoneTransit::getContenu);

  //Definit la classe Modification (non instantiable, abstraite) et le type ModificationPtr
  class_<Modification, boost::noncopyable, ModificationPtr>("Modification", no_init)
  //add_property ajoute un attribut, auquel on peut spécifier une fonction get et une fonction set (utilise comme get et set en c#)
  //dans ce cas, je specifie seulement le get, donc les attributs sont publics en read only seulement
    .add_property("position", &Modification::getPosition)
    .add_property("size", &Modification::getTaille)
    .add_property("author", &Modification::getAuteur)
    .def("apply", &Modification::effectuerModification)
    .def("update", &Modification::mettreAJour)
    .def("isAdd", &Modification::isAdd)
    .def("isRemove", &Modification::isRemove);

  //Definit Ajout heritant de Modification
  class_<Ajout, bases<Modification>>("Addition")
    .def(init<pos_t, size_t, const string&, const string&>())
    .def(init<pos_t, const string&, const string&>())
    .def(init<const Ajout&>())
    .add_property("data", &Ajout::getData);

  class_<Suppression, bases<Modification>>("Removal")
    .def(init<pos_t, size_t, const string&>())
    .def(init<const Suppression&>());

  class_<std::vector<ModificationPtr>>("Modifications")
    .def(vector_indexing_suite<std::vector<ModificationPtr>, true >());
}
