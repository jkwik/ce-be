from backend import db

def makeTemplateSlugUnique(template_model, slug):
    """
    Takes in a slugified template name and makes it unique. It does so by querying the db and checking if there are
    any records LIKE the slug. If there is, then it increments the count and appends it to the slug
    """
    existing_slugs = db.session.query(template_model).filter(template_model.slug.contains(slug)).order_by(template_model.slug).all()
    # Split the slug so we can check if the last word is a number (count), if it is, we increment by 1 and add
    # it to the end of the slug
    if len(existing_slugs) != 0:
        slug_array = str(existing_slugs[len(existing_slugs) - 1].slug).split("-")
        if slug_array[len(slug_array)-1].isdigit():
            slug = slug + "-" + str(int(slug_array[len(slug_array)-1]) + 1)
        else:
            slug = slug + "-" + "1"

    return slug
