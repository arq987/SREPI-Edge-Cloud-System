BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID('dbo.SREPI_Reserva_Config', 'U') IS NULL
    BEGIN
        CREATE TABLE dbo.SREPI_Reserva_Config (
            ID_Config INT NOT NULL,
            Valor INT NOT NULL,
            Unidad VARCHAR(10) NOT NULL,
            Fecha_Actualizacion DATETIME2(7) NOT NULL CONSTRAINT DF_SREPI_Reserva_Config_Fecha DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_SREPI_Reserva_Config PRIMARY KEY (ID_Config),
            CONSTRAINT CK_SREPI_Reserva_Config_Unidad CHECK (Unidad IN ('horas', 'dias'))
        );

        INSERT INTO dbo.SREPI_Reserva_Config (ID_Config, Valor, Unidad)
        VALUES (1, 2, 'horas');
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;
