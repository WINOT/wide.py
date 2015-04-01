/****************************************************************************
 *  Classe:       ZoneTransit                                               *
 *  Auteur:       Mariane Maynard                                           *
 *  Description:  Classe servant a stocker temporairement les modifications *
 *                d'un fichier sur le serveur en attendant d'etre resolues  *
 ****************************************************************************/

#include <vector>
#include <boost/python/tuple.hpp>
#include "PaquetModifications.h"
#include "Fichier.h"
#include "Types.h"

#ifndef ZONE_TRANSIT
#define ZONE_TRANSIT

using std::vector;
using std::string;

using namespace types;

class ZoneTransit
{
  private:
    vector<PaquetModifications> _paquetModifications; //ce vecteur sert a la gestion interne d'ecriture et de mise a jour des modifications
    vector<ModificationPtr> _modifications; //ce vecteur sera retourne a l'application lorsqu'ecrireModifications est appele
    Fichier _fichier;

  public:
    ZoneTransit() = default;

    ZoneTransit(const string& contenu) noexcept
      : _paquetModifications{}
      , _modifications{}
      , _fichier{contenu}
    {
      //// TODO Make reserve based on maximum modification constant
      _paquetModifications.reserve(500);
      _modifications.reserve(500);
    }

    //ajoute la modification a la liste
    void add(const vector<ModificationPtr>& pm)
    {
      _paquetModifications.push_back(PaquetModifications(pm));

      //On ajoute graduellement a ce vecteur pour amortir le cout d'un appel a ecrireModifications
      _modifications.insert(_modifications.end(), pm.begin(), pm.end());
    }

    void add(const ModificationPtr& m)
    {
      _paquetModifications.push_back(PaquetModifications(vector<ModificationPtr>(1,m)));

      //On ajoute graduellement a ce vecteur pour amortir le cout d'un appel a ecrireModifications
      _modifications.push_back(m);
    }

    //effectue les modifications
    boost::python::tuple ecrireModifications()
    {
      //On effectue les modifications par "paquet" pour eviter que les modifications
      //d'un meme paquet se mettent a jour inutilement entre elles
      for(auto it = _paquetModifications.begin(); it != _paquetModifications.end(); ++it)
      {
        it->effectuerModification(_fichier);
        mettreAJourModifications(it);
      }

      boost::python::tuple modifications = boost::python::make_tuple(0,_modifications);

      _paquetModifications.clear();
      _modifications.clear();

      return modifications;
    }

    string getContenu() const {return _fichier.getContenu();}

    bool estVide() const noexcept {return _modifications.empty();}

  private:
    void mettreAJourModifications(vector<PaquetModifications>::iterator it)
    {
      PaquetModifications& modification = *it;
      for(++it; it != _paquetModifications.end(); ++it)
      {
        it->mettreAJour(modification);
      }
    }
};

#endif //ZONE_TRANSIT

