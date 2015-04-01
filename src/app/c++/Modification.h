/****************************************************************************
 *  Classe:       Modification                                              *
 *  Auteur:       Mariane Maynard                                           *
 *  Description:  Representation d'une modification de l'utilisateur        *
 ****************************************************************************/

#ifndef MODIFICATION
#define MODIFICATION

#include "Fichier.h"
#include "Types.h"

using namespace types;

class Modification
{
  private:
    pos_t _position;
    size_t _taille;
    string _auteur;
    //uint _versionID;

  public:
    Modification() = default;

    Modification(pos_t position, size_t taille, const string& auteur)
      : _position{position}
      , _taille{taille}
      , _auteur{auteur}
    {}

    virtual ~Modification() = default;
    virtual pos_t getPosition() const noexcept {return _position;}
    virtual size_t getTaille() const noexcept {return _taille;}
    virtual string getAuteur() const noexcept {return _auteur;}
    virtual void effectuerModification(Fichier& fichier) = 0;

    virtual void mettreAJour(const Modification& m1)
    {
        m1.mettreAJourAutre(*this);
    }

    virtual void setPosition(pos_t value) noexcept {_position = value;}
    virtual void setTaille(size_t value) noexcept {_taille = value;}
    virtual bool isAdd() const = 0;
    virtual bool isRemove() const = 0;
    virtual void updateTaille(const Modification& m1) = 0;

  protected:
    virtual void mettreAJourAutre(Modification& m2) const = 0;
};

#endif //MODIFICATION
