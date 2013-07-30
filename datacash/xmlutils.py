def create_element(doc, parent, tag, value=None, attributes=None):
    """
    Creates an XML element
    """
    ele = doc.createElement(tag)
    parent.appendChild(ele)
    if value:
        text = doc.createTextNode(u"%s" % value)
        ele.appendChild(text)
    if attributes:
        [ele.setAttribute(k, str(v)) for k, v in attributes.items()]
    return ele
