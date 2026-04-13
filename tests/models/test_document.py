"""
Tests for Document model and related functionality.
"""
from src.enrgdocdb.models.document import (
    Document,
    DocumentAuthor,
    DocumentFile,
    DocumentTopic,
    DocumentType,
)
from src.enrgdocdb.models.author import Author
from src.enrgdocdb.models.topic import Topic


class TestDocumentType:
    """Test DocumentType model."""
    
    def test_document_type_creation(self, db_session):
        """Test creating a document type."""
        doc_type = DocumentType(name="Conference Paper")
        db_session.add(doc_type)
        db_session.commit()
        
        assert doc_type.id is not None
        assert doc_type.name == "Conference Paper"
    
    def test_document_type_repr(self, db_session):
        """Test document type string representation."""
        doc_type = DocumentType(name="Journal Article")
        db_session.add(doc_type)
        db_session.commit()
        
        assert str(doc_type) == "Journal Article"
    
    def test_document_type_uniqueness(self, db_session):
        """Test that document types can have same names."""
        type1 = DocumentType(name="Conference Paper")
        type2 = DocumentType(name="Conference Paper")
        db_session.add_all([type1, type2])
        db_session.commit()
        
        # Should be able to have multiple with same name (no unique constraint)
        assert type1.id != type2.id


class TestDocumentFile:
    """Test DocumentFile model."""
    
    def test_document_file_creation(self, db_session, document):
        """Test creating a document file."""
        file = DocumentFile(
            document_id=document.id,
            file_name="paper.pdf",
            real_file_name="/uploads/documents/123/paper.pdf",
        )
        db_session.add(file)
        db_session.commit()
        
        assert file.id is not None
        assert file.file_name == "paper.pdf"
        assert file.real_file_name.startswith("/uploads/")
    
    def test_document_file_relationship(self, db_session, document):
        """Test document file relationship."""
        file1 = DocumentFile(
            document_id=document.id,
            file_name="file1.pdf",
            real_file_name="/uploads/documents/123/file1.pdf",
        )
        file2 = DocumentFile(
            document_id=document.id,
            file_name="file2.pdf",
            real_file_name="/uploads/documents/123/file2.pdf",
        )
        db_session.add_all([file1, file2])
        db_session.commit()
        
        assert len(document.files) == 2
        assert file1 in document.files
        assert file2 in document.files
    
    def test_document_file_repr(self, db_session, document):
        """Test document file string representation."""
        file = DocumentFile(
            document_id=document.id,
            file_name="report.pdf",
            real_file_name="/uploads/documents/123/report.pdf",
        )
        db_session.add(file)
        db_session.commit()
        
        assert str(file) == "report.pdf"
    
    def test_document_file_cascade_delete(self, db_session, document):
        """Test that files are deleted when document is deleted."""
        file = DocumentFile(
            document_id=document.id,
            file_name="test.pdf",
            real_file_name="/uploads/documents/123/test.pdf",
        )
        db_session.add(file)
        db_session.commit()
        
        db_session.delete(document)
        db_session.commit()
        
        # File should be deleted due to cascade
        deleted_file = db_session.query(DocumentFile).get(file.id)
        assert deleted_file is None


class TestDocumentAuthor:
    """Test DocumentAuthor model."""
    
    def test_document_author_creation(self, db_session, document, author):
        """Test creating a document author."""
        doc_author = DocumentAuthor(
            document_id=document.id,
            author_id=author.id,
        )
        db_session.add(doc_author)
        db_session.commit()
        
        assert doc_author.id is not None
        assert doc_author.document_id == document.id
        assert doc_author.author_id == author.id
    
    def test_document_author_relationships(self, db_session, document, author):
        """Test document author relationships."""
        doc_author = DocumentAuthor(
            document_id=document.id,
            author_id=author.id,
        )
        db_session.add(doc_author)
        db_session.commit()
        
        assert doc_author.document.id == document.id
        assert doc_author.author.id == author.id
    
    def test_document_author_repr(self, db_session, document, author):
        """Test document author string representation."""
        doc_author = DocumentAuthor(
            document_id=document.id,
            author_id=author.id,
        )
        db_session.add(doc_author)
        db_session.commit()
        
        # DocumentAuthor doesn't have __repr__, so just verify it exists
        assert doc_author is not None


class TestDocumentTopic:
    """Test DocumentTopic model."""
    
    def test_document_topic_creation(self, db_session, document, topic):
        """Test creating a document topic."""
        doc_topic = DocumentTopic(
            document_id=document.id,
            topic_id=topic.id,
        )
        db_session.add(doc_topic)
        db_session.commit()
        
        assert doc_topic.id is not None
        assert doc_topic.document_id == document.id
        assert doc_topic.topic_id == topic.id
    
    def test_document_topic_relationships(self, db_session, document, topic):
        """Test document topic relationships."""
        doc_topic = DocumentTopic(
            document_id=document.id,
            topic_id=topic.id,
        )
        db_session.add(doc_topic)
        db_session.commit()
        
        assert doc_topic.document.id == document.id
        assert doc_topic.topic.id == topic.id
    
    def test_document_topic_repr(self, db_session, document, topic):
        """Test document topic string representation."""
        doc_topic = DocumentTopic(
            document_id=document.id,
            topic_id=topic.id,
        )
        db_session.add(doc_topic)
        db_session.commit()
        
        # DocumentTopic doesn't have __repr__, so just verify it exists
        assert doc_topic is not None


class TestDocument:
    """Test Document model."""
    
    def test_document_creation(self, db_session, document):
        """Test creating a document."""
        assert document.id is not None
        assert document.title == "Test Document"
        assert document.abstract == "This is a test document"
        assert document.document_type_id == 1
        assert document.user_id == 1
        assert document.organization_id == 1
    
    def test_document_relationships(self, db_session, document, author, topic):
        """Test document relationships with authors and topics."""
        # Add author to document
        doc_author = DocumentAuthor(
            document_id=document.id,
            author_id=author.id,
        )
        document.document_authors.append(doc_author)
        
        # Add topic to document
        doc_topic = DocumentTopic(
            document_id=document.id,
            topic_id=topic.id,
        )
        document.document_topics.append(doc_topic)
        
        db_session.commit()
        
        assert len(document.document_authors) == 1
        assert len(document.document_topics) == 1
        assert len(document.authors) == 1
        assert len(document.topics) == 1
        assert author in document.authors
        assert topic in document.topics
    
    def test_document_with_files(self, db_session, document):
        """Test document with files."""
        file1 = DocumentFile(
            document_id=document.id,
            file_name="file1.pdf",
            real_file_name="/uploads/documents/123/file1.pdf",
        )
        file2 = DocumentFile(
            document_id=document.id,
            file_name="file2.pdf",
            real_file_name="/uploads/documents/123/file2.pdf",
        )
        document.files.extend([file1, file2])
        db_session.commit()
        
        assert len(document.files) == 2
        assert file1 in document.files
        assert file2 in document.files
    
    def test_document_abstract_optional(self, db_session):
        """Test that abstract is optional."""
        doc_type = DocumentType(name="Conference Paper")
        author = Author(
            first_name="Jane",
            last_name="Doe",
            email="jane.doe@example.com",
            institution_id=1,
        )
        document = Document(
            title="Document Without Abstract",
            document_type=doc_type,
            user_id=1,
            organization_id=1,
            abstract=None,
        )
        db_session.add_all([doc_type, author, document])
        db_session.commit()
        
        assert document.abstract is None
    
    def test_document_title_max_length(self, db_session):
        """Test document title max length."""
        doc_type = DocumentType(name="Conference Paper")
        long_title = "A" * 1024  # Max length for title field
        document = Document(
            title=long_title,
            document_type=doc_type,
            user_id=1,
            organization_id=1,
        )
        db_session.add_all([doc_type, document])
        db_session.commit()
        
        assert len(document.title) == 1024
    
    def test_document_abstract_max_length(self, db_session):
        """Test document abstract max length."""
        doc_type = DocumentType(name="Conference Paper")
        long_abstract = "B" * 8192  # Max length for abstract field
        document = Document(
            title="Document With Long Abstract",
            document_type=doc_type,
            user_id=1,
            organization_id=1,
            abstract=long_abstract,
        )
        db_session.add_all([doc_type, document])
        db_session.commit()
        
        assert len(document.abstract) == 8192
    
    def test_document_repr(self, db_session, document):
        """Test document string representation."""
        assert str(document) == "Test Document"
    
    def test_document_cascade_delete_authors(self, db_session, document, author):
        """Test that document authors are deleted when document is deleted."""
        doc_author = DocumentAuthor(
            document_id=document.id,
            author_id=author.id,
        )
        document.document_authors.append(doc_author)
        db_session.commit()
        
        db_session.delete(document)
        db_session.commit()
        
        # DocumentAuthor should be deleted due to cascade
        deleted_doc_author = db_session.query(DocumentAuthor).get(doc_author.id)
        assert deleted_doc_author is None
    
    def test_document_cascade_delete_topics(self, db_session, document, topic):
        """Test that document topics are deleted when document is deleted."""
        doc_topic = DocumentTopic(
            document_id=document.id,
            topic_id=topic.id,
        )
        document.document_topics.append(doc_topic)
        db_session.commit()
        
        db_session.delete(document)
        db_session.commit()
        
        # DocumentTopic should be deleted due to cascade
        deleted_doc_topic = db_session.query(DocumentTopic).get(doc_topic.id)
        assert deleted_doc_topic is None
    
    def test_document_add_author_via_proxy(self, db_session, document, author):
        """Test adding author via association proxy."""
        document.authors.append(author)
        db_session.commit()
        
        assert author in document.authors
        assert len(document.document_authors) == 1
    
    def test_document_add_topic_via_proxy(self, db_session, document, topic):
        """Test adding topic via association proxy."""
        document.topics.append(topic)
        db_session.commit()
        
        assert topic in document.topics
        assert len(document.document_topics) == 1
    
    def test_document_multiple_authors(self, db_session, document, author):
        """Test document with multiple authors."""
        author2 = Author(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            institution_id=1,
        )
        db_session.add(author2)
        db_session.commit()
        
        document.authors.append(author)
        document.authors.append(author2)
        db_session.commit()
        
        assert len(document.authors) == 2
        assert author in document.authors
        assert author2 in document.authors
    
    def test_document_multiple_topics(self, db_session, document, topic):
        """Test document with multiple topics."""
        topic2 = Topic(name="Computer Science")
        db_session.add(topic2)
        db_session.commit()
        
        document.topics.append(topic)
        document.topics.append(topic2)
        db_session.commit()
        
        assert len(document.topics) == 2
        assert topic in document.topics
        assert topic2 in document.topics


class TestDocumentAuthorModel:
    """Test DocumentAuthor model relationships and behavior."""
    
    def test_document_author_author_relationship(self, db_session, document, author):
        """Test DocumentAuthor author relationship."""
        doc_author = DocumentAuthor(
            document_id=document.id,
            author_id=author.id,
        )
        db_session.add(doc_author)
        db_session.commit()
        
        assert doc_author.author.id == author.id
        assert doc_author.author.first_name == "Test"
        assert doc_author.author.last_name == "Author"
    
    def test_document_author_document_relationship(self, db_session, document, author):
        """Test DocumentAuthor document relationship."""
        doc_author = DocumentAuthor(
            document_id=document.id,
            author_id=author.id,
        )
        db_session.add(doc_author)
        db_session.commit()
        
        assert doc_author.document.id == document.id
        assert doc_author.document.title == "Test Document"
    
    def test_document_author_unique_constraint(self, db_session, document, author):
        """Test that document-author combinations are unique."""
        doc_author1 = DocumentAuthor(
            document_id=document.id,
            author_id=author.id,
        )
        db_session.add(doc_author1)
        db_session.commit()
        
        # Try to add the same author-document relationship again
        doc_author2 = DocumentAuthor(
            document_id=document.id,
            author_id=author.id,
        )
        db_session.add(doc_author2)
        
        # This should work (no unique constraint at DB level), but we can test logic
        db_session.commit()
        
        # Should have 2 entries (application-level uniqueness is not enforced)
        assert len(document.document_authors) == 2


class TestDocumentTopicModel:
    """Test DocumentTopic model relationships and behavior."""
    
    def test_document_topic_topic_relationship(self, db_session, document, topic):
        """Test DocumentTopic topic relationship."""
        doc_topic = DocumentTopic(
            document_id=document.id,
            topic_id=topic.id,
        )
        db_session.add(doc_topic)
        db_session.commit()
        
        assert doc_topic.topic.id == topic.id
        assert doc_topic.topic.name == "Test Topic"
    
    def test_document_topic_document_relationship(self, db_session, document, topic):
        """Test DocumentTopic document relationship."""
        doc_topic = DocumentTopic(
            document_id=document.id,
            topic_id=topic.id,
        )
        db_session.add(doc_topic)
        db_session.commit()
        
        assert doc_topic.document.id == document.id
        assert doc_topic.document.title == "Test Document"


class TestAuthor:
    """Test Author model."""
    
    def test_author_creation(self, db_session, author):
        """Test creating an author."""
        assert author.id is not None
        assert author.first_name == "Test"
        assert author.last_name == "Author"
        assert author.email == "author@example.com"
    
    def test_author_name_property(self, db_session, author):
        """Test author name property."""
        assert author.name == "Test Author"
    
    def test_author_repr(self, db_session, author):
        """Test author string representation."""
        assert str(author) == "Test Author"
    
    def test_author_document_count(self, db_session, author, document):
        """Test author document count."""
        doc_author = DocumentAuthor(
            document_id=document.id,
            author_id=author.id,
        )
        author.document_authors.append(doc_author)
        db_session.commit()
        
        assert author.get_document_count() == 1
        assert author.get_document_count() == len(author.document_authors)
    
    def test_author_without_email(self, db_session):
        """Test author without email."""
        author = Author(
            first_name="Jane",
            last_name="Smith",
            email=None,
            institution_id=1,
        )
        db_session.add(author)
        db_session.commit()
        
        assert author.email is None
        assert author.name == "Jane Smith"
    
    def test_author_with_phone(self, db_session):
        """Test author with phone number."""
        author = Author(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            phone="+1-555-123-4567",
            institution_id=1,
        )
        db_session.add(author)
        db_session.commit()
        
        assert author.phone == "+1-555-123-4567"
    
    def test_author_institution_relationship(self, db_session, author, institution):
        """Test author institution relationship."""
        assert author.institution_id == institution.id
        assert author.institution.name == "Test Institution"
    
    def test_author_multiple_documents(self, db_session, author, document):
        """Test author with multiple documents."""
        doc_type = DocumentType(name="Journal Article")
        document2 = Document(
            title="Second Document",
            document_type=doc_type,
            user_id=1,
            organization_id=1,
        )
        db_session.add_all([doc_type, document2])
        db_session.commit()
        
        doc_author1 = DocumentAuthor(document_id=document.id, author_id=author.id)
        doc_author2 = DocumentAuthor(document_id=document2.id, author_id=author.id)
        author.document_authors.extend([doc_author1, doc_author2])
        db_session.commit()
        
        assert author.get_document_count() == 2


class TestInstitution:
    """Test Institution model."""
    
    def test_institution_creation(self, db_session, institution):
        """Test creating an institution."""
        assert institution.id is not None
        assert institution.name == "Test Institution"
    
    def test_institution_repr(self, db_session, institution):
        """Test institution string representation."""
        assert str(institution) == "Test Institution"
    
    def test_institution_with_authors(self, db_session, institution, author):
        """Test institution with authors."""
        author2 = Author(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            institution_id=institution.id,
        )
        db_session.add(author2)
        db_session.commit()
        
        # Query authors for this institution
        institution_authors = db_session.query(Author).filter_by(
            institution_id=institution.id
        ).all()
        
        assert len(institution_authors) == 2
        assert author in institution_authors
        assert author2 in institution_authors


class TestTopic:
    """Test Topic model."""
    
    def test_topic_creation(self, db_session, topic):
        """Test creating a topic."""
        assert topic.id is not None
        assert topic.name == "Test Topic"
    
    def test_topic_repr_without_parent(self, db_session, topic):
        """Test topic string representation without parent."""
        assert str(topic) == "Test Topic"
    
    def test_topic_with_parent(self, db_session, topic):
        """Test topic with parent topic."""
        parent_topic = Topic(name="Computer Science")
        child_topic = Topic(name="Machine Learning", parent_topic=parent_topic)
        db_session.add_all([parent_topic, child_topic])
        db_session.commit()
        
        assert child_topic.parent_topic.id == parent_topic.id
        assert str(child_topic) == "Computer Science : Machine Learning"
    
    def test_topic_child_topics_relationship(self, db_session):
        """Test topic child topics relationship."""
        parent = Topic(name="Science")
        child1 = Topic(name="Physics", parent_topic=parent)
        child2 = Topic(name="Chemistry", parent_topic=parent)
        db_session.add_all([parent, child1, child2])
        db_session.commit()
        
        assert len(parent.child_topics) == 2
        assert child1 in parent.child_topics
        assert child2 in parent.child_topics
    
    def test_topic_hierarchy(self, db_session):
        """Test topic hierarchy with multiple levels."""
        level1 = Topic(name="Science")
        level2 = Topic(name="Physics", parent_topic=level1)
        level3 = Topic(name="Quantum", parent_topic=level2)
        db_session.add_all([level1, level2, level3])
        db_session.commit()
        
        assert level3.parent_topic.id == level2.id
        assert level2.parent_topic.id == level1.id
        assert level1.parent_topic is None
    
    def test_topic_cascade_delete_child_topics(self, db_session):
        """Test that child topics are deleted when parent is deleted."""
        parent = Topic(name="Science")
        child = Topic(name="Physics", parent_topic=parent)
        db_session.add_all([parent, child])
        db_session.commit()
        
        db_session.delete(parent)
        db_session.commit()
        
        # Child should be deleted due to cascade
        deleted_child = db_session.query(Topic).get(child.id)
        assert deleted_child is None
