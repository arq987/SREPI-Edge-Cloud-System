BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID('dbo.DDA_Categoria_Config', 'U') IS NULL
    BEGIN
        CREATE TABLE dbo.DDA_Categoria_Config (
            ID_Categoria INT NOT NULL,
            Multiplicador_XP DECIMAL(3, 2) NOT NULL,
            Fecha_Actualizacion DATETIME2(7) NOT NULL CONSTRAINT DF_DDA_Categoria_Config_Fecha DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_DDA_Categoria_Config PRIMARY KEY (ID_Categoria),
            CONSTRAINT FK_DDA_Categoria_Config_Categoria FOREIGN KEY (ID_Categoria) REFERENCES dbo.Categorias(ID_Categoria)
        );
    END;

    IF OBJECT_ID('dbo.DDA_Producto_Config', 'U') IS NULL
    BEGIN
        CREATE TABLE dbo.DDA_Producto_Config (
            SKU VARCHAR(20) NOT NULL,
            Descuento_Extra DECIMAL(5, 2) NOT NULL,
            Fecha_Actualizacion DATETIME2(7) NOT NULL CONSTRAINT DF_DDA_Producto_Config_Fecha DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_DDA_Producto_Config PRIMARY KEY (SKU),
            CONSTRAINT FK_DDA_Producto_Config_Producto FOREIGN KEY (SKU) REFERENCES dbo.Productos(SKU),
            CONSTRAINT CK_DDA_Producto_Descuento CHECK (Descuento_Extra >= -20 AND Descuento_Extra <= 40)
        );
    END;

    IF OBJECT_ID('dbo.DDA_Config_Historial', 'U') IS NULL
    BEGIN
        CREATE TABLE dbo.DDA_Config_Historial (
            ID_Historial INT IDENTITY(1, 1) NOT NULL,
            Tipo VARCHAR(20) NOT NULL,
            Clave VARCHAR(50) NOT NULL,
            Valor_Anterior DECIMAL(10, 4) NULL,
            Valor_Nuevo DECIMAL(10, 4) NOT NULL,
            Fecha_Registro DATETIME2(7) NOT NULL CONSTRAINT DF_DDA_Config_Historial_Fecha DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_DDA_Config_Historial PRIMARY KEY (ID_Historial)
        );
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;
