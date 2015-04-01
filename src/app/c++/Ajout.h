/****************************************************************************
 *  Classe:       Ajout                                                     *
 *  Auteur:       Mariane Maynard                                           *
 *  Description:  Representation d'un ajout de l'utilisateur                *
 ****************************************************************************/

#ifndef AJOUT
#define AJOUT

#include "Fichier.h"
#include "Types.h"
#include "Modification.h"

using namespace types;

class Ajout : public Modification
{
  private:
    string _data;

  public:
    Ajout() = default;

    Ajout(pos_t position, size_t taille, const string& data, const string& auteur)
      : Modification(position, taille, auteur)
      , _data{data}
    {}

    Ajout(pos_t position, const string& data, const string& auteur)
      : Modification(position, data.size(), auteur)
      , _data{data}
    {}

    virtual void effectuerModification(Fichier& fichier) override
    {
      fichier.inserer(_data.c_str(), getPosition(), getTaille());
    }

    virtual void mettreAJourAutre(Modification& m2) const override
    {
      //cas possibles:
      //this (m1) est un ajout et est positionne apres m2
      //rien a faire

      //this (m1) est un ajout et est positionne avant m2 (pos)
      pos_t posAutre = m2.getPosition();
      if(getPosition() <= posAutre)
          m2.setPosition(posAutre + getTaille());
    }


    virtual void updateTaille(const Modification& m1) override
    {
      //this = m2
      //On assume que m1 est necessairement une suppression.
      //Etant donne que m2 (this) est un ajout, il n'y a rien a faire ici.
      //La taille - qui est celle de son contenu - n'est pas affectee.
    }

    string getData() const {return _data;}

    virtual bool isAdd() const override
    {
      return true;
    }

    virtual bool isRemove() const override
    {
      return false;
    }
};

#endif //AJOUT
