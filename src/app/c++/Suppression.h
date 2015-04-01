/****************************************************************************
 *  Classe:       Suppression                                               *
 *  Auteur:       Mariane Maynard                                           *
 *  Description:  Representation d'une supression de l'utilisateur          *
 ****************************************************************************/

#ifndef SUPPRESSION
#define SUPPRESSION

#include "Fichier.h"
#include "Types.h"
#include "Modification.h"
#include <algorithm>

using namespace types;
using std::max;

class Suppression : public Modification
{
  public:
    Suppression() = default;

    Suppression(pos_t position, size_t taille, const string& auteur)
      : Modification(position, taille, auteur)
    {}

    virtual void effectuerModification(Fichier& fichier) override
    {
      size_t finFichier = fichier.getContenu().size();

      //Avec les mises a jour et les modifications precedentes,
      //il se peut que la taille de la suppression depasse la fin du fichier

      //On met a jour la taille pour eviter de supprimer plus que necessaire
      if(getPosition() + getTaille() > finFichier)
        setTaille(finFichier - getPosition());

      fichier.supprimer(getPosition(), getTaille());
    }

    virtual void mettreAJourAutre(Modification& m2) const override
    {
      //this = m1
      //m1 est une suppression et est positionnee avant m2
      pos_t posAutre = m2.getPosition();
      if(getPosition() < m2.getPosition())
      {
          //Si m2 est une suppression et que les deux s'empietent (overlap)
          //il faut recalculer la taille de la modification
          m2.updateTaille(*this);

          m2.setPosition(posAutre - getTaille());

          //La nouvelle position de m2 se trouvera avant celle de m1
          //si et seulement si m2 empiete (overlaps) m1
          //Dans ce cas, on veut ramener sa position a celle de m1
          m2.setPosition(max(m2.getPosition(), getPosition()));
      }

      //this est une suppression et est positionnee apres m2
      //rien a faire
    }

    virtual void updateTaille(const Modification& m1) override
    {
      //this = m2
      //on assume que m1 est necessairement une suppression
      //calcule la taille de l'empietement
      //m1: 0...........5........
      //m2:  ......2.............7
      //overlapsSize = 0 + 5 -2 = 3

      int overlapsSize = m1.getPosition() + m1.getTaille() - getPosition();
      overlapsSize = max(overlapsSize, 0);
      //s'ils ne s'empietent pas, on ramene la taille de l'empietement a 0
      //m1: 0.........3.............
      //m2:  ..............4........6
      //overlapsSize calcule = -1 => 0 (pas d'overlaps)

      //on reduit la taille de l'overlapsSize
      size_t tailleCourante = getTaille();
      setTaille(overlapsSize <= tailleCourante ? tailleCourante - overlapsSize : 0);
      //si m2 est completement contenu dans m1, alors m2 a un impact nul (taille == 0)
      //m1: 0..............7
      //m2:  ...2........5...
      //overlapsSize calcule = 7 - 2 = 5 => 3 puisque m2 est de taille 3
    }

    virtual bool isAdd() const override
    {
      return false;
    }

    virtual bool isRemove() const override
    {
      return true;
    }
};

#endif //SUPPRESSION
