import sqlite3
from sqlite3 import Error as SqliteError
from pydantic import BaseModel
from typing import (
    get_origin,
    get_args,
    Any,
    Type,
    TypeVar,
    Union,
    Annotated,
    Optional,
    _SpecialForm,
    Callable,
    Iterator,
    Literal,
    Tuple,
    List,
    Sequence,
    Collection,
    Dict,
    Mapping,
)
from pathlib import Path
from datetime import datetime
from functools import wraps
import json

_BaseModel = TypeVar("_BaseModel", bound=BaseModel)
BaseModelType = type[BaseModel]
BaseModelInstanceOrType = Union[
    BaseModel, BaseModelType
]  # So tables can be created from instances of models or the models themselves

SQLDanticNull = Literal["NULL"]
SQLDanticTEXT = Literal["TEXT"]
SQLDanticBLOB = Literal["BLOB"]
SQLDanticINTEGER = Literal["INTEGER"]
SQLDanticREAL = Literal["REAL"]
SQLDanticTIMESTAMP = Literal["TIMESTAMP"]
SQLDanticUNION = Literal["UNION"]
SQLDanticANNOTATED = Literal["ANNOTATED"]
SQLDanticSEQUENCE = Literal["SEQUENCE"]
SQLDanticMAPPING = Literal["MAPPING"]
SQLDanticUNKNOWN = Literal["UNKNOWN"]

SQLDanticType = Union[  # Values used to determine SQL type of a field in a model
    _SpecialForm,  # Unions, Annotated, Sequences, Literals, ClassVar, etc. (Recursively unpacked until the FIRST concrete type or BaseModel is found)
    BaseModelType,  # Any subclass of pydantic.BaseModel is handled as a separate table
    SQLDanticNull,  # SQL NULL
    SQLDanticTEXT,  # SQL TEXT
    SQLDanticBLOB,  # SQL BLOB
    SQLDanticINTEGER,  # SQL INTEGER
    SQLDanticREAL,  # SQL REAL
    SQLDanticTIMESTAMP,  # SQL TIMESTAMP
    SQLDanticUNION,  # typing.Union
    SQLDanticANNOTATED,  # typing.Annotated
    SQLDanticSEQUENCE,  # typing.Sequence (list, tuple, etc.)
    SQLDanticMAPPING,  # typing.Mapping (dict, etc.)
    SQLDanticUNKNOWN,  # Any other type that is not handled by the above and is handled by the default mapping
    None,  # So Optionals don't raise errors
]

SQLDanticTypeMap = Mapping[Any, SQLDanticType]
# Default mapping of Python types to SQL types (can be updated when initializing the BaseDB class)
SQLDANTIC_TYPE_MAP: SQLDanticTypeMap = {
    None: "NULL",
    str: "TEXT",
    bytes: "BLOB",
    bytearray: "BLOB",
    bool: "INTEGER",
    int: "INTEGER",
    float: "REAL",
    datetime: "TIMESTAMP",
    Union: "UNION",
    Annotated: "ANNOTATED",
    Sequence: "SEQUENCE",
    Mapping: "MAPPING",
}

# Represents a field in a model with its type and item type (if it is a sequence)
SQLDanticFieldType = Tuple[SQLDanticType, Optional[Union[SQLDanticType, Tuple[SQLDanticType, SQLDanticType]]]]
# Fields of a model mapped to their SQLDatnicField
SQLDanticFieldTypes = Dict[str, SQLDanticFieldType]

OptionalArgs = Optional[Collection[Any]]  # Optional arguments to be passed to functions below
TableNameGetter = Union[Callable, Sequence[Callable]]  # Function or list of functions to derive table name from model
TableNameTransformer = Union[
    Callable, Sequence[Callable]
]  # Function or list of functions to transform table name (e.g. lowercase, pluralize, add some prefix, etc.)
PrimaryKeyGetterOrFieldName = Union[
    Callable, str
]  # Function or field name to derive primary key from model (e.g. first field, field with name 'id', etc.)

Query = Tuple[str, Tuple]  # A single SQL query and its values to be executed
QueryDict = Dict[str, Tuple]  # A mapping of SQL queries to their values to be executed


# Table Name Derivation Functions
def get_table_name_from_schema(model: BaseModelType, *args) -> Optional[str]:
    core_schema = model.__pydantic_core_schema__
    if model_name := core_schema.get("model_name"):
        return model_name
    elif schema := core_schema.get("schema"):
        if cls := schema.get("cls"):
            return cls.__name__
        elif (config := schema.get("config")) and (title := config.get("title")):
            return title
        elif (subschema := schema.get("schema")) and (model_name := subschema.get("model_name")):
            return model_name


def get_table_name_from_class_name(model: BaseModelType, *args) -> str:
    return model.__name__


def get_table_name_from__bases__(model: BaseModelType, depth: int = 1) -> str:
    if (parent_at_depth := model.__bases__[depth]) is BaseModel:
        raise ValueError("Cannot derive table name from BaseModel")
    return parent_at_depth.__name__


def get_table_name_from__mro__(model: BaseModelType, depth: int = 1) -> str:
    if (parent_at_depth := model.__mro__[depth]) is BaseModel:
        raise ValueError("Cannot derive table name from BaseModel")
    return parent_at_depth.__name__


def get_table_name_from_class_attr(model: BaseModelType, table_name_attr: str = "table_name") -> str:
    return getattr(model, table_name_attr)


def _call_with_optional_args(func: Callable, operand: Any, args: OptionalArgs) -> Any:
    if args is None:
        return func(operand)
    return func(operand, *args)


def get_table_name(
    model: BaseModelType,
    table_name_getter: TableNameGetter,
    table_name_getter_args: OptionalArgs = None,
) -> str:
    if not isinstance(table_name_getter, Collection):
        table_name_getter = (table_name_getter,)
    for getter in table_name_getter:
        try:
            if table_name := _call_with_optional_args(getter, model, table_name_getter_args):
                return table_name
        except Exception as e:
            print(e)
            continue
    raise ValueError("Could not derive table name. Tried: ", table_name_getter)


# Table name transformers
def pluralize(table_name: str) -> str:
    return table_name + ("s" if not table_name.endswith("s") else "es")


def transform_table_name(
    table_name: str,
    table_name_transformer: TableNameTransformer,
    table_name_transformer_args: OptionalArgs,
) -> str:
    if not isinstance(table_name_transformer, Collection):
        table_name_transformer = (table_name_transformer,)
    for transformer in table_name_transformer:
        table_name = _call_with_optional_args(transformer, table_name, table_name_transformer_args)
    return table_name


# Primary Key Derivation Functions
def get_primary_key_from_first_field(model: BaseModelType) -> str:
    return next(iter(model.model_fields))


def get_primary_key(
    model: BaseModelType,
    primary_key_getter: PrimaryKeyGetterOrFieldName,
    primary_key_getter_args: OptionalArgs,
) -> str:
    if isinstance(primary_key_getter, str):
        return primary_key_getter
    return _call_with_optional_args(primary_key_getter, model, primary_key_getter_args)


# Type checking utilities
def is_type_and_subclass(
    annotation: Union[type, SQLDanticType, None],
    _class_or_tuple: Union[type, Tuple[type]],
) -> bool:
    """Checks that the annotation is a type before checking if it is a subclass of _class_or_tuple"""
    return isinstance(annotation, type) and issubclass(annotation, _class_or_tuple)


def is_base_model(annotation: Union[type, SQLDanticType, None]) -> bool:
    """Checks if the annotation is a subclass of pydantic.BaseModel"""
    return is_type_and_subclass(annotation, BaseModel)


def get_sqldantic_type(
    annotation: Union[type, SQLDanticType, None],
    sqldantic_type_map: SQLDanticTypeMap = SQLDANTIC_TYPE_MAP,
) -> SQLDanticFieldType:
    if is_base_model(annotation):
        return annotation, None
    elif isinstance(annotation, BaseModel):
        return type(annotation), None

    origin = get_origin(annotation)
    if origin in (Annotated, Union) or isinstance(type(origin), _SpecialForm):  # is subclass?
        for arg in get_args(annotation):
            if arg is None:
                continue
            elif (sqldantic_type_and_item_type := get_sqldantic_type(arg))[0] not in (
                "UNION",
                "ANNOTATED",
            ):
                return sqldantic_type_and_item_type

    elif is_type_and_subclass(origin, Sequence):
        sequence_args = get_args(annotation)
        if not sequence_args:
            return "SEQUENCE", "UNKNOWN"
        item_type, _ = get_sqldantic_type(sequence_args[0])
        return "SEQUENCE", item_type

    elif is_type_and_subclass(origin, Mapping):
        mapping_args = get_args(annotation)
        if not mapping_args:
            return "MAPPING", "UNKNOWN"
        key_type, _ = get_sqldantic_type(mapping_args[0])
        val_type, _ = get_sqldantic_type(mapping_args[1])
        return "MAPPING", (key_type, val_type)

    return sqldantic_type_map.get(annotation, "UNKNOWN"), None


def get_model_sqldantic_fields(
    model: BaseModelType, sqldantic_type_map: SQLDanticTypeMap = SQLDANTIC_TYPE_MAP
) -> Dict[str, SQLDanticFieldType]:
    return {
        field_name: get_sqldantic_type(field_info.annotation, sqldantic_type_map)
        for field_name, field_info in model.model_fields.items()
    }


class SQLDanticSchema:
    def __init__(
        self,
        model: Union[_BaseModel, Type[_BaseModel]],
        sqldantic_type_map: SQLDanticTypeMap = SQLDANTIC_TYPE_MAP,
        table_name_getter: TableNameGetter = [
            get_table_name_from_class_name,
            get_table_name_from_schema,
        ],
        table_name_getter_args: OptionalArgs = None,
        table_name_transformer: TableNameTransformer = [str.lower, pluralize],
        table_name_transformer_args: Optional[Collection] = None,
        primary_key_getter: PrimaryKeyGetterOrFieldName = get_primary_key_from_first_field,
        primary_key_getter_args: OptionalArgs = None,
    ) -> None:
        if isinstance(model, BaseModel):
            self.model: Type[_BaseModel] = type(model)
        else:
            self.model: Type[_BaseModel] = model

        table_name = get_table_name(self.model, table_name_getter, table_name_getter_args)
        if not table_name:
            raise ValueError("Could not derive table name. Tried: ", table_name_getter)

        self.table_name = transform_table_name(table_name, table_name_transformer, table_name_transformer_args)
        self.primary_key = get_primary_key(self.model, primary_key_getter, primary_key_getter_args)
        self.sqldantic_fields = get_model_sqldantic_fields(self.model, sqldantic_type_map)


def catch_sqlite_errors(func):
    @wraps(func)
    def wrapper(instance, *args, **kwargs):
        try:
            return func(instance, *args, **kwargs)
        except SqliteError as e:
            if instance.ignore_sqlite_errors and (
                instance.ignore_sqlite_errors is True
                or type(e) in instance.ignore_sqlite_errors  # So sqlite exceptions classes can passed directly
                or (
                    (error_str := str(e))
                    and any(error_str.startswith(ignored_error) for ignored_error in instance.ignore_sqlite_errors)
                )
            ):
                # print(e, args, kwargs)
                return None
            else:
                # Raise the error if it is not to be ignored
                raise e

    return wrapper


class BaseDB:
    SEQUENCE_SEPARATOR = ","

    def __init__(
        self,
        db_file: Union[str, bytes, Path] = ":memory:",
        *models: BaseModelInstanceOrType,
        sqldantic_type_map: SQLDanticTypeMap = SQLDANTIC_TYPE_MAP,
        table_name_getter: TableNameGetter = [
            get_table_name_from_class_name,
            get_table_name_from_schema,
        ],
        table_name_transformer: TableNameTransformer = [str.lower, pluralize],
        connect_on_init: bool = True,
        ignore_sqlite_errors: Union[bool, Collection[Union[SqliteError, str]]] = {
            "UNIQUE constraint failed",
        },
    ) -> None:
        self.db_file = db_file
        self.sqldantic_type_map = sqldantic_type_map
        self.table_name_getter = table_name_getter
        self.table_name_transformer = table_name_transformer
        if connect_on_init:
            self.create_connection()
            if models:
                self.create_tables_from_models(*models)
        else:
            self.connected = False
        self.ignore_sqlite_errors = ignore_sqlite_errors

    def get_sqldantic_schema(self, model: Union[_BaseModel, Type[_BaseModel]]) -> SQLDanticSchema:
        return SQLDanticSchema(
            model=model,
            sqldantic_type_map=self.sqldantic_type_map,
            table_name_getter=self.table_name_getter,
            table_name_transformer=self.table_name_transformer,
        )

    def __del__(self) -> None:
        self.close_connection()

    @catch_sqlite_errors
    def create_connection(self) -> None:
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()
        self.connected = True

    @catch_sqlite_errors
    def close_connection(self) -> None:
        if self.connected:
            self.conn.close()
            self.connected = False

    @catch_sqlite_errors
    def execute_and_commit(self, query: str, values: Tuple) -> None:
        self.cursor.execute(query, values)
        self.conn.commit()
        # print(f"Executed {query} with values {values}")

    def execute_queries(self, query_gen: Union[Iterator[Query], Tuple[Query]], remove_duplicates=False) -> None:
        query_hashes = set() if remove_duplicates else None
        for query_values in query_gen:
            if query_hashes is None:
                self.execute_and_commit(*query_values)
            elif (query_hash := hash(query_values)) not in query_hashes:
                query_hashes.add(query_hash)
                self.execute_and_commit(*query_values)

    @catch_sqlite_errors
    def recusive_create_table_queries(
        self, model: BaseModelInstanceOrType, if_not_exists: bool = True
    ) -> Iterator[Query]:
        sqldantic_schema = self.get_sqldantic_schema(model)

        column_defs = []
        foreign_keys = []
        for (
            field_name,
            sqldantic_type_and_item_type,
        ) in sqldantic_schema.sqldantic_fields.items():
            sqldantic_type, item_type = sqldantic_type_and_item_type

            if is_base_model(sqldantic_type):
                sub_schema = yield from self.recusive_create_table_queries(sqldantic_type, if_not_exists)

                column_defs.append(f"{field_name} TEXT")
                foreign_keys.append(
                    f"FOREIGN KEY ({field_name}) REFERENCES {sub_schema.table_name} ({sub_schema.primary_key})"
                )

            elif sqldantic_type == "SEQUENCE":
                if is_base_model(item_type):
                    item_schema = yield from self.recusive_create_table_queries(item_type, if_not_exists)
                column_defs.append(f"{field_name} TEXT")

            elif sqldantic_type == "MAPPING" and isinstance(item_type, tuple):
                key_type, val_type = item_type
                if is_base_model(key_type):
                    key_schema = yield from self.recusive_create_table_queries(key_type, if_not_exists)
                if is_base_model(val_type):
                    val_schema = yield from self.recusive_create_table_queries(val_type, if_not_exists)
                column_defs.append(f"{field_name} TEXT")
            else:
                column_defs.append(f"{field_name} {sqldantic_type}")
                if field_name == sqldantic_schema.primary_key:
                    column_defs[-1] += " PRIMARY KEY"

        columns = ", ".join(column_defs + foreign_keys)
        if_not_exists_statement = "IF NOT EXISTS" if if_not_exists else ""
        query = f"CREATE TABLE {if_not_exists_statement} {sqldantic_schema.table_name} ({columns})"
        yield (query, ())
        return sqldantic_schema

    def create_tables_from_model(self, model: BaseModelInstanceOrType, if_not_exists: bool = True) -> None:
        query_gen = self.recusive_create_table_queries(model, if_not_exists)
        self.execute_queries(query_gen)

    def create_tables_from_models(self, *models: BaseModelInstanceOrType, if_not_exists: bool = True) -> None:
        for model in models:
            query_gen = self.recusive_create_table_queries(model, if_not_exists)
            self.execute_queries(query_gen)

    @catch_sqlite_errors
    def recursive_modify_table_queries(self, model: BaseModel, query_facory: Callable) -> Iterator[Query]:
        sqldantic_schema = self.get_sqldantic_schema(model)

        model_dict = {}
        for (
            field_name,
            sqldantic_type_and_item_type,
        ) in sqldantic_schema.sqldantic_fields.items():
            sqldantic_type, item_type = sqldantic_type_and_item_type
            value = getattr(model, field_name)

            if value is None:
                model_dict[field_name] = None

            elif is_base_model(sqldantic_type):
                value_schema = yield from self.recursive_modify_table_queries(value, query_facory)
                model_dict[field_name] = str(getattr(value, value_schema.primary_key))

            elif sqldantic_type == "SEQUENCE":
                if is_base_model(item_type):
                    sequence_values = []
                    for item in value:
                        item_schema = yield from self.recursive_modify_table_queries(item, query_facory)
                        sequence_values.append(getattr(item, item_schema.primary_key))

                    model_dict[field_name] = self.SEQUENCE_SEPARATOR.join(
                        str(item) if not isinstance(item, str) else item for item in sequence_values
                    )

                elif value is None:
                    model_dict[field_name] = None
                else:
                    model_dict[field_name] = self.SEQUENCE_SEPARATOR.join(
                        str(item) if not isinstance(item, str) else item for item in value
                    )

            elif sqldantic_type == "MAPPING":
                # Todo handle hashable BaseModels as keys
                key_type, val_type = item_type
                if is_base_model(val_type):
                    mapping = {}
                    for key, val in value.items():
                        val_schema = yield from self.recursive_modify_table_queries(val, query_facory)
                        mapping[key] = getattr(val, val_schema.primary_key)
                    model_dict[field_name] = json.dumps(mapping)
                else:
                    model_dict[field_name] = json.dumps(value)

            elif sqldantic_type == "UNKNOWN":
                if is_base_model(item_type):
                    value_schema = yield from self.recursive_modify_table_queries(value, query_facory)
                    model_dict[field_name] = getattr(value, value_schema.primary_key)
                else:
                    model_dict[field_name] = json.dumps(value)

            else:
                model_dict[field_name] = value

        query, values = query_facory(sqldantic_schema, model_dict)
        yield (query, values)
        return sqldantic_schema

    @staticmethod
    def insert_query_factory(sqldantic_schema: SQLDanticSchema, model_dict: dict) -> Query:
        columns = ", ".join(model_dict)
        placeholders = ", ".join("?" for _ in model_dict)
        values = tuple(model_dict.values())
        query = f"INSERT INTO {sqldantic_schema.table_name} ({columns}) VALUES ({placeholders})"
        return query, values

    def insert_model(self, model: BaseModel) -> None:
        query_gen = self.recursive_modify_table_queries(model, self.insert_query_factory)
        self.execute_queries(query_gen)

    def insert_models(self, *models: BaseModel) -> None:
        for model in models:
            self.insert_model(model)

    @staticmethod
    def update_query_factory(sqldantic_schema: SQLDanticSchema, model_dict: dict) -> Query:
        primary_key_value = model_dict.pop(sqldantic_schema.primary_key)
        set_clause = ", ".join(f"{key} = ?" for key in model_dict)
        condition_clause = f"{sqldantic_schema.primary_key} = ?"
        values = tuple(model_dict.values()) + (primary_key_value,)
        query = f"UPDATE {sqldantic_schema.table_name} SET {set_clause} WHERE {condition_clause}"
        return query, values

    def update_model(self, model: BaseModel) -> None:
        query_gen = self.recursive_modify_table_queries(model, self.update_query_factory)
        self.execute_queries(query_gen)

    def update_models(self, *models: BaseModel) -> None:
        for model in models:
            self.update_model(model)

    @staticmethod
    def delete_query_factory(sqldantic_schema: SQLDanticSchema, model_dict: dict) -> Query:
        primary_key_value = model_dict[sqldantic_schema.primary_key]
        condition_clause = f"{sqldantic_schema.primary_key} = ?"
        values = (primary_key_value,)
        query = f"DELETE FROM {sqldantic_schema.table_name} WHERE {condition_clause}"
        return query, values

    def recursively_delete_model(self, model: BaseModel) -> None:
        query_gen = self.recursive_modify_table_queries(model, self.delete_query_factory)
        self.execute_queries(query_gen)

    def delete_model(self, model: BaseModel) -> None:
        sqldantic_schema = self.get_sqldantic_schema(model)
        primary_key_value = getattr(model, sqldantic_schema.primary_key)
        query = f"DELETE FROM {sqldantic_schema.table_name} WHERE {sqldantic_schema.primary_key} = ?"
        values = (primary_key_value,)
        self.execute_queries(((query, values),))

    @staticmethod
    def primary_key_select_query_factory(sqldantic_schema: SQLDanticSchema, *args, **kwargs) -> Query:
        if args:
            placeholder = ", ".join("?" for _ in args)
            condition_clause = f"WHERE {sqldantic_schema.primary_key} IN ({placeholder})"
        else:
            condition_clause = ""
        values = args
        query = f"SELECT * FROM {sqldantic_schema.table_name} {condition_clause}"
        return query, values

    @staticmethod
    def by_keys_select_query_factory(sqldantic_schema: SQLDanticSchema, *args, **kwargs) -> Query:
        contitions = []
        values = []
        for key, value in kwargs.items():
            if isinstance(value, Sequence):
                contitions.append(f"{key} IN ({', '.join('?' for _ in value)})")
                values.extend(value)
            else:
                contitions.append(f"{key} = ?")
                values.append(value)
        condition_clause = " AND ".join(contitions)
        query = f"SELECT * FROM {sqldantic_schema.table_name} WHERE {condition_clause}"
        return query, tuple(values)

    @catch_sqlite_errors
    def iter_models(
        self,
        model: Union[_BaseModel, Type[_BaseModel]],
        *select_query_factory_args,
        select_query_factory: Callable,
        **select_query_factory_kwargs,
    ) -> Iterator[_BaseModel]:
        sqldantic_schema = self.get_sqldantic_schema(model)

        query, values = select_query_factory(
            sqldantic_schema, *select_query_factory_args, **select_query_factory_kwargs
        )
        if not query.startswith("SELECT") or query.count("?") != len(values):
            raise ValueError(
                "select_query_factory must return a SELECT query that results in all the values needed to construct the model"
                "and must have the same number of placeholders as the number of values returned by the select_query_factory"
            )

        self.execute_queries(((query, values),))

        for row in self.cursor.fetchall():
            model_dict = {}
            for row_index, (field_name, sqldantic_type_and_item_type) in enumerate(
                sqldantic_schema.sqldantic_fields.items()
            ):
                sqldantic_type, item_type = sqldantic_type_and_item_type
                value = row[row_index]
                if value is None:
                    model_dict[field_name] = None

                elif is_base_model(sqldantic_type):
                    try:
                        model_dict[field_name] = next(
                            self.iter_models(
                                sqldantic_type,
                                value,
                                select_query_factory=select_query_factory,
                                **select_query_factory_kwargs,
                            )
                        )
                    except StopIteration:
                        model_dict[field_name] = None
                elif sqldantic_type == "SEQUENCE":
                    sequence_values = value.split(self.SEQUENCE_SEPARATOR)
                    if is_base_model(item_type):
                        model_dict[field_name] = list(
                            self.iter_models(
                                item_type,
                                *sequence_values,
                                select_query_factory=select_query_factory,
                                **select_query_factory_kwargs,
                            )
                        )
                    else:
                        model_dict[field_name] = sequence_values
                elif sqldantic_type == "MAPPING" and isinstance(item_type, tuple):
                    mapping = json.loads(value)
                    key_type, val_type = item_type
                    if (key_is_basemodel := is_base_model(val_type)) or (val_is_basemodel := is_base_model(val_type)):
                        if key_is_basemodel:
                            keys_gen = self.iter_models(
                                key_type,
                                *mapping.keys(),
                                select_query_factory=select_query_factory,
                                **select_query_factory_kwargs,
                            )
                        else:
                            keys_gen = mapping.keys()
                        if val_is_basemodel:
                            vals_gen = self.iter_models(
                                val_type,
                                *mapping.values(),
                                select_query_factory=select_query_factory,
                                **select_query_factory_kwargs,
                            )
                        else:
                            vals_gen = mapping.values()
                        model_dict[field_name] = dict(zip(keys_gen, vals_gen))
                    else:
                        model_dict[field_name] = mapping

                elif sqldantic_type == "UNKNOWN":
                    if is_base_model(item_type):
                        model_dict[field_name] = next(
                            self.iter_models(
                                item_type,
                                value,
                                select_query_factory=select_query_factory,
                                **select_query_factory_kwargs,
                            )
                        )
                    else:
                        model_dict[field_name] = json.loads(value)

                else:
                    model_dict[field_name] = value

            model_instance: _BaseModel = sqldantic_schema.model(**model_dict)
            yield model_instance

    def get_models(
        self,
        model: Union[_BaseModel, Type[_BaseModel]],
        *select_query_factory_args,
        select_query_factory: Callable = primary_key_select_query_factory,
        **select_query_factory_kwargs,
    ) -> List[_BaseModel]:
        return list(
            self.iter_models(
                model,
                *select_query_factory_args,
                select_query_factory=select_query_factory,
                **select_query_factory_kwargs,
            )
        )

    def get_models_by_primary_key(
        self, model: Union[_BaseModel, Type[_BaseModel]], *primary_keys: str
    ) -> List[_BaseModel]:
        return self.get_models(model, *primary_keys)

    def get_models_by_id(self, model: Union[_BaseModel, Type[_BaseModel]], *ids: str) -> List[_BaseModel]:
        return self.get_models(model, *ids)

    def get_model(
        self,
        model: Union[_BaseModel, Type[_BaseModel]],
        *select_query_factory_args,
        select_query_factory: Callable = primary_key_select_query_factory,
        **select_query_factory_kwargs,
    ) -> Optional[_BaseModel]:
        try:
            return next(
                self.iter_models(
                    model,
                    *select_query_factory_args,
                    select_query_factory=select_query_factory,
                    **select_query_factory_kwargs,
                )
            )
        except StopIteration:
            return None

    def get_model_by_primary_key(
        self, model: Union[_BaseModel, Type[_BaseModel]], *primary_keys: str
    ) -> Optional[_BaseModel]:
        return self.get_model(model, *primary_keys)

    def get_model_by_id(self, model: Union[_BaseModel, Type[_BaseModel]], *ids: str) -> Optional[_BaseModel]:
        return self.get_model(model, *ids)
