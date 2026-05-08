BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID('dbo.DDA_Params_Config', 'U') IS NULL
    BEGIN
        CREATE TABLE dbo.DDA_Params_Config (
            ID_Config       INT NOT NULL CONSTRAINT PK_DDA_Params_Config PRIMARY KEY,
            Dias_Roja       INT NOT NULL CONSTRAINT DF_DDA_Params_Dias_Roja       DEFAULT 2,
            Dias_Amarilla   INT NOT NULL CONSTRAINT DF_DDA_Params_Dias_Amarilla   DEFAULT 3,
            Desc_Roja       DECIMAL(5, 2) NOT NULL CONSTRAINT DF_DDA_Params_Desc_Roja       DEFAULT 70,
            Desc_Amarilla   DECIMAL(5, 2) NOT NULL CONSTRAINT DF_DDA_Params_Desc_Amarilla   DEFAULT 50,
            Desc_Verde      DECIMAL(5, 2) NOT NULL CONSTRAINT DF_DDA_Params_Desc_Verde      DEFAULT 20,
            XP_Roja         INT NOT NULL CONSTRAINT DF_DDA_Params_XP_Roja         DEFAULT 100,
            XP_Amarilla     INT NOT NULL CONSTRAINT DF_DDA_Params_XP_Amarilla     DEFAULT 50,
            XP_Verde        INT NOT NULL CONSTRAINT DF_DDA_Params_XP_Verde        DEFAULT 20,
            Multiplicador_XP DECIMAL(4, 2) NOT NULL CONSTRAINT DF_DDA_Params_Mult_XP DEFAULT 1.0,
            Fecha_Actualizacion DATETIME2(7) NOT NULL CONSTRAINT DF_DDA_Params_Fecha DEFAULT SYSUTCDATETIME()
        );

        INSERT INTO dbo.DDA_Params_Config (ID_Config, Dias_Roja, Dias_Amarilla, Desc_Roja, Desc_Amarilla, Desc_Verde, XP_Roja, XP_Amarilla, XP_Verde, Multiplicador_XP)
        VALUES (1, 2, 3, 70, 50, 20, 100, 50, 20, 1.0);
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;
