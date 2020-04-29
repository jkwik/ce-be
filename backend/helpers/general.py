from backend import db
import math

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

def paginate(items, page, page_size):
    """
    Paginate takes in a list of items, a page and page_size. It returns a subset of the items
    based on the pagination parameters passed in.

    Arguments:
        - items (list): any list of objects
        - page (int): current page to be viewed (pages start at 1, not 0)
        - page_size (int): number of items to return with the page

    Returns:
        - items (list): paginated subset of items
        - current_page (int): current page that is requested (will be same as page argument)
        - end_page (int): the last page in this list given the page and page_size
    """

    # Subtract 1 from page because pages start at 1
    page = page - 1
    page_size = page_size
    end_page = math.ceil(len(items) / page_size)

    # If the starting index is greater than the number of sessions, return empty items
    starting_index = page * page_size
    if starting_index >= len(items):
        return [], page + 1, end_page
    else:
        # Otherwise, add items that are in the range of starting_index -> starting_index + page_size.
        # We stop and return the items if the index is out of range.
        paginated_items = []
        for i in range(starting_index, starting_index + page_size):
            if i >= len(items):
                break
            paginated_items.append(items[i])
        
        return paginated_items, page + 1, end_page
